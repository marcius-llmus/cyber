from apply_patch_py.models import AddFile, DeleteFile, UpdateFile
from apply_patch_py.parser import PatchParser

from app.patches.enums import ParsedPatchOperation

from .base import (
    ParsedPatch,
    PatchRepresentationExtractor,
)


class CodexPatchRepresentationExtractor(PatchRepresentationExtractor):
    @staticmethod
    def _count_hunk_lines(hunk: AddFile | DeleteFile | UpdateFile) -> tuple[int, int]:
        if isinstance(hunk, AddFile):
            return len(hunk.content.splitlines()), 0

        if isinstance(hunk, DeleteFile):
            return 0, 0

        if isinstance(hunk, UpdateFile):
            additions = 0
            deletions = 0
            for chunk in hunk.chunks:
                common = sum(
                    1
                    for old, new in zip(chunk.old_lines, chunk.new_lines, strict=False)
                    if old == new
                )
                additions += max(0, len(chunk.new_lines) - common)
                deletions += max(0, len(chunk.old_lines) - common)
            return additions, deletions

        raise ValueError(f"Unsupported codex patch hunk type: {type(hunk)}")

    def extract(self, raw_text: str) -> list[ParsedPatch]:
        parser = PatchParser()
        patch = parser.parse(raw_text)

        parsed_items: list[ParsedPatch] = []
        for hunk in patch.hunks:
            if isinstance(hunk, AddFile):
                new_path = str(hunk.path)
                additions, deletions = self._count_hunk_lines(hunk)
                parsed_items.append(
                    ParsedPatch(
                        diff=hunk.diff,
                        old_path=None,
                        new_path=new_path,
                        operation=ParsedPatchOperation.ADD,
                        is_rename=False,
                        is_added_file=True,
                        is_removed_file=False,
                        is_modified_file=False,
                        path=new_path,
                        additions=additions,
                        deletions=deletions,
                    )
                )
                continue

            if isinstance(hunk, DeleteFile):
                old_path = str(hunk.path)
                additions, deletions = self._count_hunk_lines(hunk)
                parsed_items.append(
                    ParsedPatch(
                        old_path=old_path,
                        new_path=None,
                        operation=ParsedPatchOperation.DELETE,
                        is_rename=False,
                        is_added_file=False,
                        is_removed_file=True,
                        is_modified_file=False,
                        path=old_path,
                        additions=additions,
                        deletions=deletions,
                    )
                )
                continue

            if isinstance(hunk, UpdateFile):
                old_path = str(hunk.path)
                new_path = (
                    str(hunk.move_to)
                    if isinstance(hunk, UpdateFile) and hunk.move_to
                    else None
                )
                additions, deletions = self._count_hunk_lines(hunk)
                new_path = new_path or old_path
                operation = (
                    ParsedPatchOperation.RENAME
                    if new_path != old_path
                    else ParsedPatchOperation.MODIFY
                )
                is_rename = operation == ParsedPatchOperation.RENAME
                parsed_items.append(
                    ParsedPatch(
                        diff=hunk.diff,
                        old_path=old_path,
                        new_path=new_path,
                        operation=operation,
                        is_rename=is_rename,
                        is_added_file=False,
                        is_removed_file=False,
                        is_modified_file=not is_rename,
                        path=new_path,
                        additions=additions,
                        deletions=deletions,
                    )
                )
                continue

            raise ValueError(f"Unsupported codex patch hunk type: {type(hunk)}")

        return parsed_items
