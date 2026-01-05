import logging
import re
from datetime import datetime

from llama_index.core.llms import ChatMessage

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
from app.patches.schemas import DiffPatchUpdate

logger = logging.getLogger(__name__)


class DiffPatchService:
    def __init__(
        self,
        *,
        diff_patch_repo: DiffPatchRepository,
        llm_service: LLMService,
        project_service: ProjectService,
        codebase_service: CodebaseService,
    ):
        self.diff_patch_repo = diff_patch_repo
        self.llm_service = llm_service
        self.project_service = project_service
        self.codebase_service = codebase_service

    async def apply_saved_patch(self, *, patch_id: int, strategy: PatchStrategy = PatchStrategy.LLM_GATHER) -> str:
        patch = await self.diff_patch_repo.get(pk=patch_id)
        if not patch:
            raise ValueError(f"DiffPatch {patch_id} not found")

        if patch.status != DiffPatchStatus.PENDING:
            return f"Patch {patch_id} is {patch.status}"

        try:
            result = await self.apply_diff(file_path=patch.file_path, diff_content=patch.diff_current, strategy=strategy)
            await self.diff_patch_repo.update(
                db_obj=patch,
                obj_in=DiffPatchUpdate(status=DiffPatchStatus.APPLIED, applied_at=datetime.now()),
            )
            return result
        except Exception as e:
            await self.diff_patch_repo.update(
                db_obj=patch,
                obj_in=DiffPatchUpdate(status=DiffPatchStatus.FAILED, error_message=str(e)),
            )
            raise

    async def apply_diff(
        self,
        *,
        file_path: str,
        diff_content: str,
        strategy: PatchStrategy = PatchStrategy.LLM_GATHER,
    ) -> str:
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to apply patches.")

        read_result = await self.codebase_service.read_file(project.path, file_path, must_exist=False)
        if read_result.status == FileStatus.SUCCESS:
            original_content = read_result.content
        elif read_result.status == FileStatus.BINARY:
            raise ValueError(f"Cannot patch binary file: {file_path}")
        else:
            raise ValueError(f"Could not read file {file_path}: {read_result.error_message}")

        if strategy != PatchStrategy.LLM_GATHER:
            raise NotImplementedError(f"Strategy {strategy} not implemented")

        patched_content = await self._apply_via_llm(original_content, diff_content)
        await self.codebase_service.write_file(project.path, file_path, patched_content)
        return f"Successfully patched {file_path}"

    async def _apply_via_llm(self, original_content: str, diff_content: str) -> str:
        llm = await self.llm_service.get_client(model_name=LLMModel.GPT_4_1_MINI, temperature=0)
        messages = [
            ChatMessage(role="system", content=DIFF_PATCHER_PROMPT),
            ChatMessage(role="user", content=f"ORIGINAL CONTENT:\n{original_content}"),
            ChatMessage(role="user", content=f"DIFF PATCH:\n{diff_content}"),
        ]
        response = await llm.achat(messages)
        return self._strip_markdown(response.message.content or "")

    @staticmethod
    def _strip_markdown(text: str) -> str:
        pattern = r"^```(?:\w+)?\s*\n(.*?)\n```$"
        match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
        if match:
            return match.group(1)
        return text
