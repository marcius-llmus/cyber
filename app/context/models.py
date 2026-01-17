from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.db import Base


class ContextFile(Base):
    __tablename__ = "context_files"

    id = Column(Integer, primary_key=True)
    session_id = Column(
        Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    user_pinned = Column(Boolean, default=False)
    hit_count = Column(Integer, default=0)

    session = relationship("ChatSession", back_populates="context_files")

    __table_args__ = (
        UniqueConstraint("session_id", "file_path", name="_session_file_uc"),
    )
