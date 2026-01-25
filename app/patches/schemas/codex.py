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
                new_path = str(hunk.path)
                parsed_items.append(
                    ParsedPatch(
                        diff=raw_text,
                        old_path=None,
                        new_path=new_path,
                        operation=ParsedPatchOperation.ADD,
                        is_rename=False,
                        is_added_file=True,
                        is_removed_file=False,
                        is_modified_file=False,
                        path=new_path,
                    )
                )
                continue

            if isinstance(hunk, DeleteFile):
                old_path = str(hunk.path)
                parsed_items.append(
                    ParsedPatch(
                        diff=raw_text,
                        old_path=old_path,
                        new_path=None,
                        operation=ParsedPatchOperation.DELETE,
                        is_rename=False,
                        is_added_file=False,
                        is_removed_file=True,
                        is_modified_file=False,
                        path=old_path,
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
                is_rename = operation == ParsedPatchOperation.RENAME
                parsed_items.append(
                    ParsedPatch(
                        diff=raw_text,
                        old_path=old_path,
                        new_path=new_path,
                        operation=operation,
                        is_rename=is_rename,
                        is_added_file=False,
                        is_removed_file=False,
                        is_modified_file=not is_rename,
                        path=new_path,
                    )
                )
                continue

            raise ValueError(f"Unsupported codex patch hunk type: {type(hunk)}")

        return parsed_items
