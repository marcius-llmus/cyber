import abc
import re
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from app.patches.enums import DiffPatchStatus, PatchProcessorType

SOURCE_PATTERN = r"^--- ([^\t\n]+)(?:\t[^\n]+)?"
TARGET_PATTERN = r"^\+\+\+ ([^\t\n]+)(?:\t[^\n]+)?"
DEV_NULL = "/dev/null"


class DiffPatchCreate(BaseModel):
    session_id: int
    turn_id: str
    diff: str
    processor_type: PatchProcessorType = PatchProcessorType.UDIFF_LLM


class DiffPatchInternalCreate(BaseModel):
    session_id: int
    turn_id: str
    diff: str
    processor_type: PatchProcessorType
    status: DiffPatchStatus
    error_message: str | None = None
    applied_at: datetime | None = None


class DiffPatchUpdate(BaseModel):
    status: DiffPatchStatus | None = None
    error_message: str | None = None
    applied_at: datetime | None = None


class ParsedPatchOperation(StrEnum):
    ADD = "ADD"
    MODIFY = "MODIFY"
    DELETE = "DELETE"
    RENAME = "RENAME"


class DiffPatchApplyPatchResult(BaseModel):
    patch_id: int
    status: DiffPatchStatus
    error_message: str | None = None

    representation: "PatchRepresentation | None" = None


class ParsedPatchItem(BaseModel):
    old_path: str | None = None
    new_path: str | None = None
    operation: ParsedPatchOperation

    @property
    def path(self) -> str:
        if self.operation == ParsedPatchOperation.DELETE:
            if not self.old_path:
                raise ValueError("Invalid patch: missing old_path")
            return self.old_path
        if not self.new_path:
            raise ValueError("Invalid patch: missing new_path")
        return self.new_path

    @property
    def is_added_file(self) -> bool:
        return self.operation == ParsedPatchOperation.ADD

    @property
    def is_removed_file(self) -> bool:
        return self.operation == ParsedPatchOperation.DELETE

    @property
    def is_rename(self) -> bool:
        return self.operation == ParsedPatchOperation.RENAME


class PatchRepresentationExtractor(abc.ABC):
    def extract(self, raw_text: str) -> list[ParsedPatchItem]:
        raise NotImplementedError


class PatchRepresentation(BaseModel):
    processor_type: PatchProcessorType
    patches: list[ParsedPatchItem]

    _EXTRACTOR_MAP: dict[PatchProcessorType, PatchRepresentationExtractor] = {}

    @classmethod
    def from_text(
        cls, *, raw_text: str, processor_type: PatchProcessorType
    ) -> "PatchRepresentation":
        extractor = cls._EXTRACTOR_MAP.get(processor_type)
        if extractor is None:
            raise NotImplementedError(
                f"Unknown PatchProcessorType: {processor_type}"
            )

        parsed_items = extractor.extract(raw_text)
        return cls(processor_type=processor_type, patches=parsed_items)

    @property
    def has_changes(self) -> bool:
        return bool(self.patches)


class ParsedDiffPatch(BaseModel):
    diff: str
    source_file: str
    target_file: str

    @classmethod
    def from_text(cls, diff_text: str) -> "ParsedDiffPatch":
        source_files = re.findall(
            SOURCE_PATTERN, diff_text, flags=re.MULTILINE | re.DOTALL
        )
        target_files = re.findall(
            TARGET_PATTERN, diff_text, flags=re.MULTILINE | re.DOTALL
        )

        if len(source_files) > 1 or len(target_files) > 1:
            raise ValueError(
                f"Multiple source and target files found: {diff_text}"
            )
        if not source_files or not target_files:
            raise ValueError("Invalid diff: missing source or target header")

        return cls(
            diff=diff_text, source_file=source_files[0], target_file=target_files[0]
        )

    @staticmethod
    def _normalize_path(path: str) -> str:
        if path.startswith("a/") or path.startswith("b/"):
            return path[2:]
        return path

    @property
    def is_rename(self) -> bool:
        if self.source_file == DEV_NULL or self.target_file == DEV_NULL:
            return False
        source = self._normalize_path(self.source_file)
        target = self._normalize_path(self.target_file)
        return source != target

    @property
    def is_added_file(self) -> bool:
        return self.source_file == DEV_NULL

    @property
    def is_removed_file(self) -> bool:
        return self.target_file == DEV_NULL

    @property
    def is_modified_file(self) -> bool:
        return not (self.is_added_file or self.is_removed_file)

    @property
    def path(self) -> str:
        filepath = self.source_file
        if filepath in (None, DEV_NULL) or (
            self.is_rename and self.target_file not in (None, DEV_NULL)
        ):
            filepath = self.target_file

        if not filepath or filepath == DEV_NULL:
            raise ValueError("Invalid diff: could not determine file path")

        return self._normalize_path(filepath)
