from datetime import datetime

from pydantic import BaseModel

from app.patches.enums import DiffPatchStatus


class DiffPatchCreate(BaseModel):
    session_id: int
    turn_id: str
    file_path: str
    diff: str


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
