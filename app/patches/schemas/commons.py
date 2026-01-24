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


class ParsedPatch(BaseModel):
    old_path: str | None = None
    new_path: str | None = None
    operation: ParsedPatchOperation
    # todo: old and new lines to be implemented

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
    def extract(self, raw_text: str) -> list[ParsedPatch]:
        raise NotImplementedError


class PatchRepresentation(BaseModel):
    processor_type: PatchProcessorType
    patches: list[ParsedPatch]

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


def _normalize_diff_path(path: str) -> str:
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def path_from_udiff_text(diff_text: str) -> str:
    source_files = re.findall(SOURCE_PATTERN, diff_text, flags=re.MULTILINE | re.DOTALL)
    target_files = re.findall(TARGET_PATTERN, diff_text, flags=re.MULTILINE | re.DOTALL)

    if len(source_files) > 1 or len(target_files) > 1:
        raise ValueError(f"Multiple source and target files found: {diff_text}")
    if not source_files or not target_files:
        raise ValueError("Invalid diff: missing source or target header")

    source_file = source_files[0]
    target_file = target_files[0]

    source_norm = _normalize_diff_path(source_file)
    target_norm = _normalize_diff_path(target_file)

    is_added = source_file == DEV_NULL
    is_removed = target_file == DEV_NULL
    is_rename = not is_added and not is_removed and source_norm != target_norm

    if is_added:
        return target_norm
    if is_removed:
        return source_norm
    if is_rename:
        return target_norm
    return target_norm