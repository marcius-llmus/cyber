from typing import Any
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from llama_index.core.llms import MessageRole
from app.core.db import Base
from app.chat.enums import ChatTurnStatus


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    turn_id = Column(String, nullable=False, index=True)
    role = Column(Enum(MessageRole, name="message_role"), nullable=False)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    blocks = Column(JSON, nullable=False, default=list, server_default='[]')

    session = relationship("ChatSession", back_populates="messages", lazy="joined")

    @property
    def content(self) -> str:
        """Derives text content from blocks."""
        if not self.blocks:
            return ""
        return "".join(b["content"] for b in self.blocks if b.get("type") == "text")

    @property
    def tool_calls(self) -> list[dict[str, Any]]:
        """Extracts tool calls from blocks."""
        if not self.blocks:
            return []
        return [b["tool_call_data"] for b in self.blocks if b.get("type") == "tool"]



class ChatTurn(Base):
    __tablename__ = "chat_turns"

    id = Column(String, primary_key=True)
    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(ChatTurnStatus, name="chat_turn_status"),
        nullable=False,
        server_default=ChatTurnStatus.PENDING,
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    session = relationship("ChatSession", back_populates="turns", lazy="joined")
