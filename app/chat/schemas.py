from pydantic import BaseModel
from typing import Any

from app.chat.enums import MessageRole


class MessageCreate(BaseModel):
    session_id: int
    role: MessageRole
    blocks: list[dict[str, Any]]


class MessageForm(BaseModel):
    message: str