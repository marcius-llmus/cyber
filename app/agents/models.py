from sqlalchemy import Column, Integer, ForeignKey, JSON
from app.core.db import Base


class WorkflowState(Base):
    __tablename__ = "workflow_states"

    session_id = Column(Integer, ForeignKey("chat_sessions.id"), primary_key=True)
    state = Column(JSON, nullable=False)
