import abc
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