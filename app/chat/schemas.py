from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.chat.enums import MessageRole, PatchStatus


class TurnRequest(BaseModel):
    user_content: str
    blocks: list[dict[str, Any]]


# diff patch is the diff itself while 'apply'
# is the action of applying a diff patch
class DiffPatchCreate(BaseModel):
    message_id: int
    session_id: int
    file_path: str
    diff_original: str
    diff_current: str
    status: PatchStatus = PatchStatus.PENDING
    error_message: str | None = None
    tool_call_id: str | None = None
    tool_run_id: str | None = None
    applied_at: datetime | None = None


class DiffPatchUpdate(BaseModel):
    status: PatchStatus | None = None
    error_message: str | None = None
    applied_at: datetime | None = None


class MessageCreate(BaseModel):
    session_id: int
    role: MessageRole
    blocks: list[dict[str, Any]]


class MessageForm(BaseModel):
    message: str
