from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel

from app.patches.enums import DiffPatchStatus, PatchProcessorType
from app.patches.schemas.base import (
    ParsedPatch,
    PatchRepresentationExtractor,
)
from app.patches.schemas.codex import CodexPatchRepresentationExtractor
from app.patches.schemas.udiff import UDiffRepresentationExtractor


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


class PatchRepresentation(BaseModel):
    processor_type: PatchProcessorType
    patches: list[ParsedPatch]

    _EXTRACTOR_MAP: ClassVar[dict[PatchProcessorType, PatchRepresentationExtractor]] = {
        PatchProcessorType.UDIFF_LLM: UDiffRepresentationExtractor(),
        PatchProcessorType.CODEX_APPLY: CodexPatchRepresentationExtractor(),
    }

    @classmethod
    def from_text(
        cls, *, raw_text: str, processor_type: PatchProcessorType
    ) -> "PatchRepresentation":
        extractor = cls._EXTRACTOR_MAP.get(processor_type)
        if extractor is None:
            raise NotImplementedError(f"Unknown PatchProcessorType: {processor_type}")

        parsed_items = extractor.extract(raw_text)
        return cls(processor_type=processor_type, patches=parsed_items)

    @property
    def has_changes(self) -> bool:
        return bool(self.patches)


class DiffPatchApplyPatchResult(BaseModel):
    patch_id: int
    status: DiffPatchStatus
    error_message: str | None = None

    representation: PatchRepresentation | None = None
