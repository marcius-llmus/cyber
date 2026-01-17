from enum import StrEnum

from pydantic import BaseModel


class ContextFileListItem(BaseModel):
    id: int
    file_path: str


class ContextFileCreate(BaseModel):
    session_id: int
    file_path: str
    user_pinned: bool = False


class ContextFileUpdate(BaseModel):
    hit_count: int | None = None
    user_pinned: bool | None = None


class Tag(BaseModel):
    name: str
    kind: str
    line: int


class ContextFileBatchUpdate(BaseModel):
    filepaths: list[str] = []


class FileStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"
    BINARY = "binary"
    IGNORED = "ignored"
    NOT_FOUND = "not_found"


class FileReadResult(BaseModel):
    file_path: str
    content: str | None = None
    status: FileStatus
    error_message: str | None = None


class FileTreeNode(BaseModel):
    """
    Represents a node in the file system (File or Folder).
    Pure domain object, unaware of UI selection state.
    """
    name: str
    path: str
    is_dir: bool
    children: list["FileTreeNode"] | None = None
