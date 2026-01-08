from sqlalchemy import Column, Integer, Float, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.db import Base


class SessionUsage(Base):
    __tablename__ = "session_usage"

    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), primary_key=True)
    cost = Column(Float, default=0.0, nullable=False)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    cached_tokens = Column(Integer, default=0, nullable=False)

    session = relationship("ChatSession", back_populates="usage_stats")


class GlobalProviderUsage(Base):
    __tablename__ = "global_provider_usage"

    provider = Column(String, primary_key=True)
    total_cost = Column(Float, default=0.0, nullable=False)
    total_input_tokens = Column(Integer, default=0, nullable=False)
    total_output_tokens = Column(Integer, default=0, nullable=False)
    total_cached_tokens = Column(Integer, default=0, nullable=False)
    last_updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
