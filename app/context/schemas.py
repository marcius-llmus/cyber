from pydantic import BaseModel


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
