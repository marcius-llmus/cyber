from typing import Any

from pydantic import BaseModel

from llama_index.core.llms import MessageRole


class TurnRequest(BaseModel):
    user_content: str
    blocks: list[dict[str, Any]]


class MessageCreate(BaseModel):
    session_id: int
    role: MessageRole
    blocks: list[dict[str, Any]]


class MessageForm(BaseModel):
    message: str
