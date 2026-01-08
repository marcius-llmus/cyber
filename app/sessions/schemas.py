from datetime import datetime
from pydantic import BaseModel
from app.core.enums import ContextStrategy, OperationalMode


class ChatSessionBase(BaseModel):
    name: str
    project_id: int


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionUpdate(BaseModel):
    operational_mode: OperationalMode | None = None
    name: str | None = None
    context_strategy: ContextStrategy | None = None


class UpdateSessionModeRequest(BaseModel):
    operational_mode: OperationalMode


class ChatSessionRead(ChatSessionBase):
    id: int
    created_at: datetime
    is_active: bool
    context_strategy: ContextStrategy
    operational_mode: OperationalMode