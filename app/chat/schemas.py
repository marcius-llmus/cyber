from pydantic import BaseModel
from typing import Any

from app.chat.enums import MessageRole


class MessageCreate(BaseModel):
    session_id: int
    role: MessageRole
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    diff_patches: list[dict[str, Any]] | None = None


class MessageForm(BaseModel):
    message: str
