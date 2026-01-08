import logging
import re
import asyncio
from datetime import datetime
from typing import Any, Awaitable, Callable

from llama_index.core.llms import ChatMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.patches.constants import DIFF_PATCHER_PROMPT
from app.patches.enums import PatchStrategy
from app.context.schemas import FileStatus
from app.context.services.codebase import CodebaseService
from app.llms.enums import LLMModel
from app.llms.services import LLMService
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.services import ProjectService
from app.patches.enums import DiffPatchStatus
from app.patches.repositories import DiffPatchRepository
from app.patches.schemas import (
    DiffPatchApplyResult,
    DiffPatchCreate,
    DiffPatchUpdate,
)
from app.core.db import DatabaseSessionManager

logger = logging.getLogger(__name__)


DIFF_BLOCK_PATTERN = r"^```diff(?:\w+)?\s*\n(.*?)(?=^```)```"
PLUS_FILE_PATTERN = re.compile(r"^\+\+\+\s+(?:[ab]/)?(?P<path>\S+)")


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

    async def apply_saved_patch(
        self,
        *,
        patch_id: int,
        strategy: PatchStrategy = PatchStrategy.LLM_GATHER,
    ) -> DiffPatchApplyResult:
        async with self.db.session() as session:
            diff_patch_repo = self.diff_patch_repo_factory(session)
            patch = await diff_patch_repo.get(pk=patch_id)
            if not patch:
                raise ValueError(f"DiffPatch {patch_id} not found")

            if patch.status != DiffPatchStatus.PENDING:
                return DiffPatchApplyResult(
                    patch_id=patch.id,
                    file_path=patch.file_path,
                    status=patch.status,
                    applied=False,
                    error_message=patch.error_message,
                )

            file_path = patch.file_path
            diff_content = patch.diff

        try:
            # apply diff can take a lot of time. that's why diff service handle its own session
            await self.apply_diff(file_path=file_path, diff_content=diff_content, strategy=strategy)
            async with self.db.session() as session:
                diff_patch_repo = self.diff_patch_repo_factory(session)
                patch = await diff_patch_repo.get(pk=patch_id)
                await diff_patch_repo.update(
                    db_obj=patch,
                    obj_in=DiffPatchUpdate(status=DiffPatchStatus.APPLIED, applied_at=datetime.now()),
                )
            return DiffPatchApplyResult(
                patch_id=patch_id,
                file_path=file_path,
                status=DiffPatchStatus.APPLIED,
                applied=True,
            )
        except Exception as e:
            async with self.db.session() as session:
                diff_patch_repo = self.diff_patch_repo_factory(session)
                patch = await diff_patch_repo.get(pk=patch_id)
                if patch:
                    await diff_patch_repo.update(
                        db_obj=patch,
                        obj_in=DiffPatchUpdate(status=DiffPatchStatus.FAILED, error_message=str(e)),
                    )
            return DiffPatchApplyResult(
                patch_id=patch_id,
                file_path=file_path,
                status=DiffPatchStatus.FAILED,
                applied=False,
                error_message=str(e),
            )

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

    async def apply_pending_by_turn_id(
        self,
        *,
        session_id: int,
        turn_id: str,
        strategy: PatchStrategy = PatchStrategy.LLM_GATHER,
    ) -> list[DiffPatchApplyResult]:
        async with self.db.session() as session:
            diff_patch_repo = self.diff_patch_repo_factory(session)
            pending = await diff_patch_repo.list_pending_by_turn(session_id=session_id, turn_id=turn_id)
        if not (tasks := [self.apply_saved_patch(patch_id=p.id, strategy=strategy) for p in pending]):
            return []

        return list(await asyncio.gather(*tasks))

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
                continue

            lines = diff_content.splitlines()
            file_path: str | None = None
            for line in lines:
                if not line.startswith("+++ "):
                    continue

                if line.strip() == "+++ /dev/null":
                    file_path = None
                    break

                match = PLUS_FILE_PATTERN.match(line)
                if match:
                    file_path = match.group("path")
                    break

            if not file_path:
                logger.warning(
                    "Single-shot diff block skipped (no +++ header path) (session_id=%s turn_id=%s).",
                    session_id,
                    turn_id,
                )
                continue

            patches.append(
                DiffPatchCreate(
                    session_id=session_id,
                    turn_id=turn_id,
                    file_path=file_path,
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
        patch_id = await self.create_patch(payload)
        return await self.apply_saved_patch(patch_id=patch_id, strategy=strategy)