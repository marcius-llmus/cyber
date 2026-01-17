from sqlalchemy import JSON, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.core.db import Base


class WorkflowState(Base):
    __tablename__ = "workflow_states"

    session_id = Column(
        Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    state = Column(JSON, nullable=False)

    session = relationship("ChatSession", back_populates="workflow_state")
