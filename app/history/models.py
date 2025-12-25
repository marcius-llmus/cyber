from sqlalchemy import (
    Column,
    DateTime,
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,

)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base
from app.settings.enums import OperationalMode


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    is_active = Column(Boolean, default=False, nullable=False, server_default="f")
    operational_mode = Column(Enum(OperationalMode), nullable=False, server_default=OperationalMode.CODING)
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
