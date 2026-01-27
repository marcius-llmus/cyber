import re
from collections.abc import Awaitable, Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.context.services.codebase import CodebaseService
from app.core.db import DatabaseSessionManager
from app.llms.services import LLMService
from app.patches.enums import DiffPatchStatus, PatchProcessorType
from app.patches.repositories import DiffPatchRepository
from app.patches.schemas import (
    DiffPatchApplyPatchResult,
    DiffPatchCreate,
    DiffPatchInternalCreate,
    DiffPatchUpdate,
    PatchRepresentation,
)
from app.patches.services.processors.codex_processor import CodexProcessor
from app.patches.services.processors.udiff_processor import UDiffProcessor
from app.projects.services import ProjectService

DIFF_BLOCK_PATTERN = r"^```diff(?:\w+)?\s*\n(.*?)(?=^```)"


class DiffPatchService:
    def __init__(
        self,
        *,
        db: DatabaseSessionManager,
        diff_patch_repo_factory: Callable[[AsyncSession], DiffPatchRepository],
        llm_service_factory: Callable[[AsyncSession], Awaitable[LLMService]],
        project_service_factory: Callable[[AsyncSession], Awaitable[ProjectService]],
        codebase_service_factory: Callable[[], Awaitable[CodebaseService]],
    ) -> None:
        self.db = db
        self.diff_patch_repo_factory = diff_patch_repo_factory
        self.llm_service_factory = llm_service_factory
        self.project_service_factory = project_service_factory
        self.codebase_service_factory = codebase_service_factory

    async def process_diff(self, payload: DiffPatchCreate) -> DiffPatchApplyPatchResult:
        patch_id = await self._create_pending_patch(payload)
        representation = None
        try:
            processor = self._build_processor(payload.processor_type)
            await processor.apply_patch(payload.diff)

            representation = PatchRepresentation.from_text(
                raw_text=payload.diff, processor_type=payload.processor_type
            )

            applied_at = datetime.now()
            await self._update_patch(
                patch_id=patch_id,
                update=DiffPatchUpdate(
                    status=DiffPatchStatus.APPLIED,
                    error_message=None,
                    applied_at=applied_at,
                ),
            )
            return DiffPatchApplyPatchResult(
                patch_id=patch_id,
                status=DiffPatchStatus.APPLIED,
                error_message=None,
                representation=representation,
            )
        except Exception as e:
            error_message = str(e)
            await self._update_patch(
                patch_id=patch_id,
                update=DiffPatchUpdate(
                    status=DiffPatchStatus.FAILED,
                    error_message=error_message,
                    applied_at=None,
                ),
            )
            return DiffPatchApplyPatchResult(
                patch_id=patch_id,
                status=DiffPatchStatus.FAILED,
                error_message=error_message,
                representation=representation,
            )

    async def _create_pending_patch(self, payload: DiffPatchCreate) -> int:
        async with self.db.session() as session:
            repo = self.diff_patch_repo_factory(session)
            created = await repo.create(
                obj_in=DiffPatchInternalCreate(
                    session_id=payload.session_id,
                    turn_id=payload.turn_id,
                    diff=payload.diff,
                    processor_type=payload.processor_type,
                    status=DiffPatchStatus.PENDING,
                    error_message=None,
                    applied_at=None,
                )
            )
            return created.id

    async def _update_patch(self, *, patch_id: int, update: DiffPatchUpdate) -> None:
        async with self.db.session() as session:
            repo = self.diff_patch_repo_factory(session)
            db_obj = await repo.get(patch_id)
            if not db_obj:
                raise ValueError(f"DiffPatch {patch_id} not found")

            await repo.update(db_obj=db_obj, obj_in=update)

    def _build_processor(self, processor_type: PatchProcessorType):
        if processor_type == PatchProcessorType.UDIFF_LLM:
            return UDiffProcessor(
                db=self.db,
                diff_patch_repo_factory=self.diff_patch_repo_factory,
                llm_service_factory=self.llm_service_factory,
                project_service_factory=self.project_service_factory,
                codebase_service_factory=self.codebase_service_factory,
            )
        if processor_type == PatchProcessorType.CODEX_APPLY:
            return CodexProcessor(
                db=self.db,
                diff_patch_repo_factory=self.diff_patch_repo_factory,
                llm_service_factory=self.llm_service_factory,
                project_service_factory=self.project_service_factory,
                codebase_service_factory=self.codebase_service_factory,
            )
        raise NotImplementedError(f"Unknown PatchProcessorType: {processor_type}")

    def extract_diffs_from_blocks(
        self,
        *,
        turn_id: str,
        session_id: int,
        blocks: list[dict[str, object]],
        processor_type: PatchProcessorType = PatchProcessorType.UDIFF_LLM,
    ) -> list[DiffPatchCreate]:
        text_content = "\n".join(
            str(b.get("content", "")) for b in (blocks or []) if b.get("type") == "text"
        )
        return self._extract_diff_patches_from_text(
            turn_id=turn_id,
            session_id=session_id,
            text=text_content,
            processor_type=processor_type,
        )

    @staticmethod
    def _extract_diff_patches_from_text(
        *,
        turn_id: str,
        session_id: int,
        text: str,
        processor_type: PatchProcessorType,
    ) -> list[DiffPatchCreate]:
        if not text:
            return []

        diff_blocks = re.findall(DIFF_BLOCK_PATTERN, text, re.DOTALL | re.MULTILINE)
        if not diff_blocks:
            return []

        patches: list[DiffPatchCreate] = []
        for diff_content in diff_blocks:
            diff_content = diff_content.strip("\n")
            if not diff_content:
                raise ValueError("Error parsing diff: No content to parse")

            patches.append(
                DiffPatchCreate(
                    session_id=session_id,
                    turn_id=turn_id,
                    diff=diff_content,
                    processor_type=processor_type,
                )
            )

        return patches
