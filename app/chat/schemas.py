from typing import Any

from pydantic import BaseModel

from llama_index.core.llms import MessageRole
from app.chat.enums import ChatTurnStatus


class TurnRequest(BaseModel):
    user_content: str
    blocks: list[dict[str, Any]]


class MessageCreate(BaseModel):
    session_id: int
    turn_id: str
    role: MessageRole
    blocks: list[dict[str, Any]]


class MessageForm(BaseModel):
    message: str


class ChatTurnCreate(BaseModel):
    id: str
    session_id: int
    status: ChatTurnStatus = ChatTurnStatus.PENDING


class ChatTurnUpdate(BaseModel):
    status: ChatTurnStatus
