from copy import deepcopy
from typing import Any

from llama_index.core.llms import MessageRole
from pydantic import BaseModel, ConfigDict, computed_field

from app.chat.enums import ChatTurnStatus
from app.patches.enums import PatchProcessorType
from app.patches.schemas.commons import PatchRepresentation


class TurnRequest(BaseModel):
    user_content: str
    blocks: list[dict[str, Any]]


class MessageCreate(BaseModel):
    session_id: int
    turn_id: str
    role: MessageRole
    blocks: list[dict[str, Any]]


# important using this to avoid mutating json in orm obj blocks
class FormattedMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: MessageRole
    blocks: list[dict[str, Any]]
    cost: float | None = None
    output_tokens: int | None = None

    @computed_field
    @property
    def content(self) -> str:
        return "".join(b["content"] for b in self.blocks if b.get("type") == "text")

    @computed_field
    @property
    def tool_calls(self) -> list[dict[str, Any]]:
        return [b for b in self.blocks if b.get("type") == "tool"]

    @classmethod
    def from_orm_message(cls, message: Any) -> "FormattedMessage":
        blocks = deepcopy(getattr(message, "blocks", []) or [])

        for block in blocks:
            if block.get("type") != "tool":
                continue

            tool = block.get("tool_call_data") or {}
            if tool.get("name") != "apply_patch":
                continue

            kwargs = tool.get("kwargs") or {}
            patch_text = str(kwargs.get("patch") or "")
            if not patch_text:
                continue

            representation = PatchRepresentation.from_text(
                raw_text=patch_text,
                processor_type=PatchProcessorType.UDIFF_LLM,
            )

            block["formatted"] = {
                "patches": [
                    {
                        "file_path": p.path,
                        "diff": p.diff,
                        "additions": p.additions,
                        "deletions": p.deletions,
                    }
                    for p in representation.patches
                ]
            }

        return cls(
            id=message.id,
            role=message.role,
            blocks=blocks,
            cost=getattr(message, "cost", None),
            output_tokens=getattr(message, "output_tokens", None),
        )


class MessageForm(BaseModel):
    message: str


class ChatTurnCreate(BaseModel):
    id: str
    session_id: int
    status: ChatTurnStatus = ChatTurnStatus.PENDING


class ChatTurnUpdate(BaseModel):
    status: ChatTurnStatus
