from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from app.core.db import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    path = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=False)

    chat_sessions = relationship(
        "ChatSession", back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )
    prompts = relationship("Prompt", back_populates="project", lazy="selectin")
    prompt_attachments = relationship(
        "ProjectPromptAttachment",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
