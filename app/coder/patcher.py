import logging
import re
from pathlib import Path

import aiofiles
import aiofiles.os

from llama_index.core.llms import ChatMessage

from app.coder.constants import DIFF_PATCHER_PROMPT
from app.coder.enums import PatchStrategy
from app.llms.enums import LLMModel
from app.llms.services import LLMService
from app.projects.services import ProjectService
from app.chat.enums import MessageRole

logger = logging.getLogger(__name__)


class PatcherService:
    def __init__(self, llm_service: LLMService, project_service: ProjectService):
        self.llm_service = llm_service
        self.project_service = project_service

    async def apply_diff(
        self,
        file_path: str,
        diff_content: str,
        strategy: PatchStrategy = PatchStrategy.LLM_GATHER,
    ) -> str:
        project = await self.project_service.get_active_project()
        if not project:
            raise ValueError("No active project found.")

        abs_project_path = Path(project.path).resolve()
        target_path = (abs_project_path / file_path).resolve()

        if not target_path.is_relative_to(abs_project_path):
            raise ValueError(f"Target file {file_path} is outside project root.")

        original_content = ""
        if target_path.exists():
            async with aiofiles.open(target_path, "r", encoding="utf-8") as f:
                original_content = await f.read()

        if strategy == PatchStrategy.LLM_GATHER:
            patched_content = await self._apply_via_llm(original_content, diff_content)
        else:
            raise NotImplementedError(f"Strategy {strategy} not implemented")

        await aiofiles.os.makedirs(target_path.parent, exist_ok=True)
        async with aiofiles.open(target_path, "w", encoding="utf-8") as f:
            await f.write(patched_content)

        return f"Successfully patched {file_path}"

    async def _apply_via_llm(self, original_content: str, diff_content: str) -> str:
        llm = await self.llm_service.get_client(
            model_name=LLMModel.GPT_4_1_MINI, temperature=0
        )

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=DIFF_PATCHER_PROMPT),
            ChatMessage(role=MessageRole.USER, content=f"ORIGINAL CONTENT:\n{original_content}"),
            ChatMessage(role=MessageRole.USER, content=f"DIFF PATCH:\n{diff_content}"),
        ]

        response = await llm.achat(messages)
        content = response.message.content

        return self._strip_markdown(content)

    @staticmethod
    def _strip_markdown(text: str) -> str:
        pattern = r"^```(?:\w+)?\s*\n(.*?)\n```$"
        match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
        if match:
            return match.group(1)
        return text
