from typing import Any
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.chat.enums import MessageRole
from app.core.db import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
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