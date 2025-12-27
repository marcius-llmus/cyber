from datetime import datetime
from pydantic import BaseModel


class ChatSessionBase(BaseModel):
    name: str
    project_id: int


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionRead(ChatSessionBase):
    id: int
    created_at: datetime
    is_active: bool
