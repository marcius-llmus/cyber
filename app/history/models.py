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
    UniqueConstraint,
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

    session = relationship("ChatSession", back_populates="messages", lazy="joined")


class ContextFile(Base):
    __tablename__ = "context_files"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    file_path = Column(String, nullable=False)

    session = relationship("ChatSession", back_populates="context_files", lazy="joined")

    __table_args__ = (UniqueConstraint("session_id", "file_path", name="_session_file_uc"),)