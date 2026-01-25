import re

from app.patches.enums import ParsedPatchOperation

from .base import (
    DEV_NULL,
    SOURCE_PATTERN,
    TARGET_PATTERN,
    ParsedPatch,
    PatchRepresentationExtractor,
)


class UnidiffParseError(ValueError):
    pass


class UDiffRepresentationExtractor(PatchRepresentationExtractor):
    def extract(self, raw_text: str) -> list[ParsedPatch]:
        source_files = re.findall(
            SOURCE_PATTERN, raw_text, flags=re.MULTILINE | re.DOTALL
        )
        target_files = re.findall(
            TARGET_PATTERN, raw_text, flags=re.MULTILINE | re.DOTALL
        )

        if len(source_files) != 1 or len(target_files) != 1:
            raise UnidiffParseError(
                "Expected a single-file unified diff (one ---/+++ header pair)."
            )

        patches: list[ParsedPatch] = []
        for source_file, target_file in zip(source_files, target_files, strict=False):
            patches.append(
                self._from_headers(source_file=source_file, target_file=target_file)
            )

        return patches

    @staticmethod
    def _normalize_path(path: str) -> str:
        if path.startswith("a/") or path.startswith("b/"):
            return path[2:]
        return path

    def _from_headers(self, *, source_file: str, target_file: str) -> ParsedPatch:
        source_norm = self._normalize_path(source_file)
        target_norm = self._normalize_path(target_file)

        is_added = source_file == DEV_NULL
        is_removed = target_file == DEV_NULL
        is_rename = not is_added and not is_removed and source_norm != target_norm

        if is_added:
            return ParsedPatch(
                old_path=None,
                new_path=target_norm,
                operation=ParsedPatchOperation.ADD,
            )

        if is_removed:
            return ParsedPatch(
                old_path=source_norm,
                new_path=None,
                operation=ParsedPatchOperation.DELETE,
            )

        if is_rename:
            return ParsedPatch(
                old_path=source_norm,
                new_path=target_norm,
                operation=ParsedPatchOperation.RENAME,
            )

        return ParsedPatch(
            old_path=source_norm,
            new_path=target_norm,
            operation=ParsedPatchOperation.MODIFY,
        )
