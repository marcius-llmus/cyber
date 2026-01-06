from datetime import datetime

from pydantic import BaseModel

from app.patches.enums import DiffPatchStatus


class DiffPatchCreate(BaseModel):
    message_id: int
    session_id: int
    file_path: str
    diff: str
    tool_call_id: str | None = None
    tool_run_id: str | None = None


class DiffPatchUpdate(BaseModel):
    status: DiffPatchStatus | None = None
    error_message: str | None = None
    applied_at: datetime | None = None


class DiffPatchApplyResult(BaseModel):
    patch_id: int
    file_path: str
    status: DiffPatchStatus
    applied: bool
    error_message: str | None = None
