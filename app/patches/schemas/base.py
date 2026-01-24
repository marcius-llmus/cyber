from abc import ABC, abstractmethod
from enum import StrEnum

from pydantic import BaseModel

SOURCE_PATTERN = r"^--- ([^\t\n]+)(?:\t[^\n]+)?"
TARGET_PATTERN = r"^\+\+\+ ([^\t\n]+)(?:\t[^\n]+)?"
DEV_NULL = "/dev/null"


class ParsedPatchOperation(StrEnum):
    ADD = "ADD"
    MODIFY = "MODIFY"
    DELETE = "DELETE"
    RENAME = "RENAME"


class ParsedPatch(BaseModel):
    old_path: str | None = None
    new_path: str | None = None
    operation: ParsedPatchOperation
    # todo: old and new lines to be implemented

    @property
    def path(self) -> str:
        if self.operation == ParsedPatchOperation.DELETE:
            if not self.old_path:
                raise ValueError("Invalid patch: missing old_path")
            return self.old_path
        if not self.new_path:
            raise ValueError("Invalid patch: missing new_path")
        return self.new_path

    @property
    def is_added_file(self) -> bool:
        return self.operation == ParsedPatchOperation.ADD

    @property
    def is_removed_file(self) -> bool:
        return self.operation == ParsedPatchOperation.DELETE

    @property
    def is_rename(self) -> bool:
        return self.operation == ParsedPatchOperation.RENAME


class PatchRepresentationExtractor(ABC):
    @abstractmethod
    def extract(self, raw_text: str) -> list[ParsedPatch]:
        raise NotImplementedError
