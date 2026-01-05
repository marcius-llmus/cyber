from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base
from app.patches.enums import DiffPatchStatus


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

    status = Column(Enum(DiffPatchStatus), default=DiffPatchStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)

    tool_call_id = Column(String, nullable=True)
    tool_run_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    applied_at = Column(DateTime(timezone=True), nullable=True)

    message = relationship("Message", back_populates="diff_patches")
    session = relationship("ChatSession", back_populates="diff_patches")
