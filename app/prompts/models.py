from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.db import Base
from app.prompts.enums import PromptType


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(Enum(PromptType), nullable=False)
    content = Column(Text, nullable=False)
    source_path = Column(String, nullable=True)
    # we keep project based prompts if project get deleted or renamed for safety instead of cascading delete
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    project = relationship("Project", back_populates="prompts", lazy="joined")
    project_attachments = relationship(
        "ProjectPromptAttachment",
        back_populates="prompt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    session_attachments = relationship(
        "SessionPromptAttachment",
        back_populates="prompt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (UniqueConstraint("name", "project_id", name="_name_project_uc"),)


class ProjectPromptAttachment(Base):
    __tablename__ = "project_prompt_attachments"

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id", ondelete="CASCADE"), primary_key=True)

    project = relationship("Project", back_populates="prompt_attachments", lazy="joined")
    prompt = relationship("Prompt", back_populates="project_attachments", lazy="joined")


class SessionPromptAttachment(Base):
    __tablename__ = "session_prompt_attachments"

    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), primary_key=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id", ondelete="CASCADE"), primary_key=True)

    session = relationship("ChatSession", back_populates="prompt_attachments", lazy="joined")
    prompt = relationship("Prompt", back_populates="session_attachments", lazy="joined")
