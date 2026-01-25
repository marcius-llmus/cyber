from abc import ABC, abstractmethod

from pydantic import BaseModel

from app.patches.enums import ParsedPatchOperation

SOURCE_PATTERN = r"^--- ([^\t\n]+)(?:\t[^\n]+)?"
TARGET_PATTERN = r"^\+\+\+ ([^\t\n]+)(?:\t[^\n]+)?"
DEV_NULL = "/dev/null"


class ParsedPatch(BaseModel):
    old_path: str | None = None
    new_path: str | None = None
    operation: ParsedPatchOperation
    # todo: old and new lines to be implemented


class PatchRepresentationExtractor(ABC):
    @abstractmethod
    def extract(self, raw_text: str) -> list[ParsedPatch]:
        raise NotImplementedError
