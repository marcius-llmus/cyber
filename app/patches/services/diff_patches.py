import logging
import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from llama_index.core.llms import ChatMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.schemas import FileStatus
from app.context.services.codebase import CodebaseService
from app.core.db import DatabaseSessionManager
from app.llms.enums import LLMModel
from app.llms.services import LLMService
from app.patches.constants import DIFF_PATCHER_PROMPT
from app.patches.enums import DiffPatchStatus, PatchStrategy
from app.patches.repositories import DiffPatchRepository
from app.patches.schemas import (
    DiffPatchApplyResult,
    DiffPatchCreate,
    DiffPatchInternalCreate,
)
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.services import ProjectService

logger = logging.getLogger(__name__)


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
    ):
        self.db = db
        self.diff_patch_repo_factory = diff_patch_repo_factory
        self.llm_service_factory = llm_service_factory
        self.project_service_factory = project_service_factory
        self.codebase_service_factory = codebase_service_factory

    async def apply_diff(
        self,
        *,
        file_path: str,
        diff_content: str,
        strategy: PatchStrategy = PatchStrategy.LLM_GATHER,
    ) -> str:
        async with self.db.session() as session:
            project_service = await self.project_service_factory(session)
            codebase_service = await self.codebase_service_factory()
            llm_service = await self.llm_service_factory(session)

            project = await project_service.get_active_project()
            if not project:
                raise ActiveProjectRequiredException("Active project required to apply patches.")

            read_result = await codebase_service.read_file(project.path, file_path, must_exist=False)
            if read_result.status == FileStatus.SUCCESS:
                original_content = read_result.content
            elif read_result.status == FileStatus.BINARY:
                raise ValueError(f"Cannot patch binary file: {file_path}")
            else:
                raise ValueError(f"Could not read file {file_path}: {read_result.error_message}")

            llm_client = await llm_service.get_client(model_name=LLMModel.GPT_4_1_MINI, temperature=0)

        if strategy != PatchStrategy.LLM_GATHER:
            raise NotImplementedError(f"Strategy {strategy} not implemented")

        patched_content = await self._apply_via_llm(llm_client, original_content, diff_content)

        async with self.db.session() as session:
            project_service = await self.project_service_factory(session)
            codebase_service = await self.codebase_service_factory()

            project = await project_service.get_active_project()
            await codebase_service.write_file(project.path, file_path, patched_content)
        return f"Successfully patched {file_path}"

    async def _apply_via_llm(self, llm_client: Any, original_content: str, diff_content: str) -> str:
        messages = [
            ChatMessage(role="system", content=DIFF_PATCHER_PROMPT),
            ChatMessage(role="user", content=f"ORIGINAL CONTENT:\n{original_content}"),
            ChatMessage(role="user", content=f"DIFF PATCH:\n{diff_content}"),
        ]
        response = await llm_client.achat(messages)
        return self._strip_markdown(response.message.content or "")

    @staticmethod
    def _strip_markdown(text: str) -> str:
        pattern = r"^```(?:\w+)?\s*\n(.*?)\n```$"
        match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
        if match:
            return match.group(1)
        return text

    def extract_diffs_from_blocks(
        self,
        *,
        turn_id: str,
        session_id: int,
        blocks: list[dict[str, Any]],
    ) -> list[DiffPatchCreate]:
        text_content = "\n".join(
            b.get("content", "") for b in (blocks or []) if b.get("type") == "text"
        )
        return self._extract_diff_patches_from_text(
            turn_id=turn_id,
            session_id=session_id,
            text=text_content,
        )

    @staticmethod
    def _extract_diff_patches_from_text(
        *,
        turn_id: str,
        session_id: int,
        text: str,
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
                )
            )

        return patches

    async def create_patch(self, payload: DiffPatchCreate) -> int:
        async with self.db.session() as session:
            diff_patch_repo = self.diff_patch_repo_factory(session)
            created = await diff_patch_repo.create(obj_in=payload)
            return created.id

    async def process_diff(
        self,
        payload: DiffPatchCreate,
        *,
        strategy: PatchStrategy = PatchStrategy.LLM_GATHER,
    ) -> DiffPatchApplyResult:
        file_path = payload.parsed.path

        applied_at: datetime | None = None
        error_message: str | None = None
        applied: False

        try:
            await self.apply_diff(file_path=file_path, diff_content=payload.diff, strategy=strategy)
            status = DiffPatchStatus.APPLIED
            applied_at = datetime.now()
        except Exception as e:
            status = DiffPatchStatus.FAILED
            error_message = str(e)

        internal_create = DiffPatchInternalCreate(
            session_id=payload.session_id,
            turn_id=payload.turn_id,
            diff=payload.diff,
            status=status,
            error_message=error_message,
            applied_at=applied_at,
        )

        async with self.db.session() as session:
            diff_patch_repo = self.diff_patch_repo_factory(session)
            created = await diff_patch_repo.create(obj_in=internal_create)
            patch_id = created.id

        return DiffPatchApplyResult(
            patch_id=patch_id,
            file_path=file_path,
            status=status,
            error_message=error_message,
        )
