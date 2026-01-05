from datetime import datetime

from pydantic import BaseModel

from app.patches.enums import DiffPatchStatus


class DiffPatchCreate(BaseModel):
    message_id: int
    session_id: int
    file_path: str
    diff_original: str
    diff_current: str
    status: DiffPatchStatus = DiffPatchStatus.PENDING
    error_message: str | None = None
    tool_call_id: str | None = None
    tool_run_id: str | None = None
    applied_at: datetime | None = None


class DiffPatchUpdate(BaseModel):
    status: DiffPatchStatus | None = None
    error_message: str | None = None
    applied_at: datetime | None = None
