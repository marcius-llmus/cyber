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
    String
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.chat.enums import MessageRole, PatchStatus
from app.core.db import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    blocks = Column(JSON, nullable=False, default=list, server_default='[]')

    session = relationship("ChatSession", back_populates="messages", lazy="joined")
    diff_patches = relationship(
        "DiffPatch",
        back_populates="message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

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


class DiffPatch(Base):
    __tablename__ = "diff_patches"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    file_path = Column(String, nullable=False)
    diff_original = Column(Text, nullable=False)
    diff_current = Column(Text, nullable=False)

    status = Column(Enum(PatchStatus), default=PatchStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)

    tool_call_id = Column(String, nullable=True)
    tool_run_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    applied_at = Column(DateTime(timezone=True), nullable=True)

    message = relationship("Message", back_populates="diff_patches")
    session = relationship("ChatSession", back_populates="diff_patches")