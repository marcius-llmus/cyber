from apply_patch_py.models import AddFile, DeleteFile, UpdateFile
from apply_patch_py.parser import PatchParser

from app.patches.enums import ParsedPatchOperation

from .base import (
    ParsedPatch,
    PatchRepresentationExtractor,
)


class CodexPatchRepresentationExtractor(PatchRepresentationExtractor):
    def extract(self, raw_text: str) -> list[ParsedPatch]:
        patch = PatchParser.parse(raw_text)

        parsed_items: list[ParsedPatch] = []
        for hunk in patch.hunks:
            if isinstance(hunk, AddFile):
                parsed_items.append(
                    ParsedPatch(
                        old_path=None,
                        new_path=str(hunk.path),
                        operation=ParsedPatchOperation.ADD,
                    )
                )
                continue

            if isinstance(hunk, DeleteFile):
                parsed_items.append(
                    ParsedPatch(
                        old_path=str(hunk.path),
                        new_path=None,
                        operation=ParsedPatchOperation.DELETE,
                    )
                )
                continue

            if isinstance(hunk, UpdateFile):
                old_path = str(hunk.path)
                new_path = str(hunk.move_to) if hunk.move_to else old_path
                operation = (
                    ParsedPatchOperation.RENAME
                    if new_path != old_path
                    else ParsedPatchOperation.MODIFY
                )
                parsed_items.append(
                    ParsedPatch(
                        old_path=old_path,
                        new_path=new_path,
                        operation=operation,
                    )
                )
                continue

            raise ValueError(f"Unsupported codex patch hunk type: {type(hunk)}")

        return parsed_items