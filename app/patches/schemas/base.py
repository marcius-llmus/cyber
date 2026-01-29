from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.patches.enums import ParsedPatchOperation


class ParsedPatch(BaseModel):
    diff: str | None = None
    old_path: str | None = None
    new_path: str | None = None
    operation: ParsedPatchOperation
    is_rename: bool
    is_added_file: bool
    is_removed_file: bool
    is_modified_file: bool
    path: str
    additions: int = 0
    deletions: int = 0


class PatchRepresentationExtractor(ABC):
    @abstractmethod
    def extract(self, raw_text: str) -> list[ParsedPatch]:
        raise NotImplementedError
