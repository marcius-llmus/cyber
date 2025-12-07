import logging
import re

from llama_index.core.llms import ChatMessage

from app.coder.constants import DIFF_PATCHER_PROMPT
from app.coder.enums import PatchStrategy
from app.llms.enums import LLMModel
from app.llms.services import LLMService
from app.context.services import WorkspaceService
from app.context.schemas import FileStatus
from app.chat.enums import MessageRole

logger = logging.getLogger(__name__)


class PatcherService:
    def __init__(self, llm_service: LLMService, context_service: WorkspaceService):
        self.llm_service = llm_service
        self.context_service = context_service

    async def apply_diff(
        self,
        file_path: str,
        diff_content: str,
        strategy: PatchStrategy = PatchStrategy.LLM_GATHER,
    ) -> str:
        read_result = await self.context_service.read_file(file_path)
        
        if read_result.status != FileStatus.SUCCESS:
            raise ValueError(f"Could not read file {file_path}: {read_result.status}")

        original_content = read_result.content

        if strategy == PatchStrategy.LLM_GATHER:
            patched_content = await self._apply_via_llm(original_content, diff_content)
        else:
            raise NotImplementedError(f"Strategy {strategy} not implemented")

        await self.context_service.save_file(file_path, patched_content)

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