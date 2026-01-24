import logging
import re
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any

from llama_index.core.llms import ChatMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.schemas import FileStatus
from app.context.services.codebase import CodebaseService
from app.core.db import DatabaseSessionManager
from app.llms.enums import LLMModel
from app.llms.services import LLMService
from app.patches.constants import DIFF_PATCHER_PROMPT
from app.patches.repositories import DiffPatchRepository
from app.patches.schemas import UDiffRepresentationExtractor
from app.patches.services.processors import BasePatchProcessor
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.services import ProjectService

logger = logging.getLogger(__name__)


class UDiffProcessor(BasePatchProcessor):
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

    async def apply_patch(self, diff: str) -> None:
        patches = UDiffRepresentationExtractor().extract(diff)
        file_path = patches[0].path
        await self._apply_file_diff(file_path=file_path, diff_content=diff)

    async def _apply_file_diff(
        self,
        *,
        file_path: str,
        diff_content: str,
    ) -> str:
        async with self.db.session() as session:
            project_service = await self.project_service_factory(session)
            codebase_service = await self.codebase_service_factory()
            llm_service = await self.llm_service_factory(session)

            project = await project_service.get_active_project()
            if not project:
                raise ActiveProjectRequiredException(
                    "Active project required to apply patches."
                )

            read_result = await codebase_service.read_file(
                project.path, file_path, must_exist=False
            )
            if read_result.status == FileStatus.SUCCESS:
                original_content = read_result.content
            elif read_result.status == FileStatus.BINARY:
                raise ValueError(f"Cannot patch binary file: {file_path}")
            else:
                raise ValueError(
                    f"Could not read file {file_path}: {read_result.error_message}"
                )

            llm_client = await llm_service.get_client(
                model_name=LLMModel.GPT_4_1_MINI, temperature=Decimal("0")
            )

        patched_content = await self._apply_via_llm(
            llm_client, original_content, diff_content
        )

        async with self.db.session() as session:
            project_service = await self.project_service_factory(session)
            codebase_service = await self.codebase_service_factory()

            project = await project_service.get_active_project()
            await codebase_service.write_file(project.path, file_path, patched_content)
        return patched_content

    async def _apply_via_llm(
        self, llm_client: Any, original_content: str, diff_content: str
    ) -> str:
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
