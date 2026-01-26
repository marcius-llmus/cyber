from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.db import Base
from app.patches.enums import DiffPatchStatus, PatchProcessorType


class DiffPatch(Base):
    __tablename__ = "diff_patches"

    id = Column(Integer, primary_key=True, index=True)
    turn_id = Column(String, nullable=False, index=True)
    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    diff = Column(Text, nullable=False)

    processor_type = Column(
        Enum(PatchProcessorType),
        nullable=False,
        index=True,
    )

    status = Column(
        Enum(DiffPatchStatus),
        default=DiffPatchStatus.PENDING,
        nullable=False,
    )
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    applied_at = Column(DateTime(timezone=True), nullable=True)

    session = relationship("ChatSession", back_populates="diff_patches")
