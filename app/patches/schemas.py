import re
from datetime import datetime
from enum import StrEnum

from apply_patch_py.models import AddFile, DeleteFile, UpdateFile
from apply_patch_py.parser import PatchParser
from pydantic import BaseModel

from app.patches.enums import DiffPatchStatus, PatchProcessorType

SOURCE_PATTERN = r"^--- ([^\t\n]+)(?:\t[^\n]+)?"
TARGET_PATTERN = r"^\+\+\+ ([^\t\n]+)(?:\t[^\n]+)?"
DEV_NULL = "/dev/null"


class UnidiffParseError(ValueError):
    pass


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
                raise UnidiffParseError("Invalid patch: missing old_path")
            return self.old_path
        if not self.new_path:
            raise UnidiffParseError("Invalid patch: missing new_path")
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


class PatchRepresentation(BaseModel):
    processor_type: PatchProcessorType
    patches: list[ParsedPatchItem]

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
            raise UnidiffParseError(
                f"Multiple source and target files found: {diff_text}"
            )
        if not source_files or not target_files:
            raise UnidiffParseError("Invalid diff: missing source or target header")

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
            raise UnidiffParseError("Invalid diff: could not determine file path")

        return self._normalize_path(filepath)


class BasePatchRepresentationExtractor:
    def extract(self, raw_text: str) -> PatchRepresentation:
        raise NotImplementedError


class UDiffRepresentationExtractor(BasePatchRepresentationExtractor):
    def extract(self, raw_text: str) -> PatchRepresentation:
        source_files = re.findall(
            SOURCE_PATTERN, raw_text, flags=re.MULTILINE | re.DOTALL
        )
        target_files = re.findall(
            TARGET_PATTERN, raw_text, flags=re.MULTILINE | re.DOTALL
        )

        patches: list[ParsedPatchItem] = []
        for source_file, target_file in zip(source_files, target_files, strict=False):
            patches.append(
                self._from_headers(source_file=source_file, target_file=target_file)
            )

        return PatchRepresentation(
            processor_type=PatchProcessorType.UDIFF_LLM, patches=patches
        )

    @staticmethod
    def _normalize_path(path: str) -> str:
        if path.startswith("a/") or path.startswith("b/"):
            return path[2:]
        return path

    def _from_headers(self, *, source_file: str, target_file: str) -> ParsedPatchItem:
        source_norm = self._normalize_path(source_file)
        target_norm = self._normalize_path(target_file)

        is_added = source_file == DEV_NULL
        is_removed = target_file == DEV_NULL
        is_rename = not is_added and not is_removed and source_norm != target_norm

        if is_added:
            return ParsedPatchItem(
                old_path=None,
                new_path=target_norm,
                operation=ParsedPatchOperation.ADD,
            )

        if is_removed:
            return ParsedPatchItem(
                old_path=source_norm,
                new_path=None,
                operation=ParsedPatchOperation.DELETE,
            )

        if is_rename:
            return ParsedPatchItem(
                old_path=source_norm,
                new_path=target_norm,
                operation=ParsedPatchOperation.RENAME,
            )

        return ParsedPatchItem(
            old_path=source_norm,
            new_path=target_norm,
            operation=ParsedPatchOperation.MODIFY,
        )


class CodexPatchRepresentationExtractor(BasePatchRepresentationExtractor):
    def extract(self, raw_text: str) -> PatchRepresentation:
        patch = PatchParser.parse(raw_text)

        parsed_items: list[ParsedPatchItem] = []
        for hunk in patch.hunks:
            if isinstance(hunk, AddFile):
                parsed_items.append(
                    ParsedPatchItem(
                        old_path=None,
                        new_path=str(hunk.path),
                        operation=ParsedPatchOperation.ADD,
                    )
                )
                continue

            if isinstance(hunk, DeleteFile):
                parsed_items.append(
                    ParsedPatchItem(
                        old_path=str(hunk.path),
                        new_path=None,
                        operation=ParsedPatchOperation.DELETE,
                    )
                )
                continue

            if isinstance(hunk, UpdateFile):
                old_path = str(hunk.path)
                new_path = str(hunk.move_to) if hunk.move_to else old_path
                operation = (
                    ParsedPatchOperation.RENAME
                    if new_path != old_path
                    else ParsedPatchOperation.MODIFY
                )
                parsed_items.append(
                    ParsedPatchItem(
                        old_path=old_path,
                        new_path=new_path,
                        operation=operation,
                    )
                )
                continue

            raise ValueError(f"Unsupported codex patch hunk type: {type(hunk)}")

        return PatchRepresentation(
            processor_type=PatchProcessorType.CODEX_APPLY,
            patches=parsed_items,
        )
