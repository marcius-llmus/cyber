from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.chat.enums import MessageRole
from app.core.db import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    is_active = Column(Boolean, default=False, nullable=False, server_default="f")
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    project = relationship("Project", back_populates="chat_sessions", lazy="joined")
    messages = relationship(
        "Message", back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )
    context_files = relationship(
        "ContextFile", back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )
    prompt_attachments = relationship(
        "SessionPromptAttachment", back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )
    workflow_state = relationship(
        "WorkflowState",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    usage_stats = relationship(
        "SessionUsage",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    tool_calls = Column(JSON, nullable=True)
    blocks = Column(JSON, nullable=False, default=list, server_default='[]')

    session = relationship("ChatSession", back_populates="messages", lazy="joined")