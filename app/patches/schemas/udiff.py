import re

from pydantic import BaseModel

from app.patches.enums import ParsedPatchOperation

from .base import (
    ParsedPatch,
    PatchRepresentationExtractor,
)

SOURCE_PATTERN = r"^--- ([^\t\n]+)(?:\t[^\n]+)?"
TARGET_PATTERN = r"^\+\+\+ ([^\t\n]+)(?:\t[^\n]+)?"
DEV_NULL = "/dev/null"


class UnidiffParseError(ValueError):
    pass


class ParsedDiffPatch(BaseModel):
    diff: str
    source_file: str
    target_file: str

    @classmethod
    def from_text(cls, diff_text: str) -> "ParsedDiffPatch":
        source_files = re.findall(
            SOURCE_PATTERN, diff_text, flags=re.MULTILINE | re.DOTALL
        )
        target_files = re.findall(
            TARGET_PATTERN, diff_text, flags=re.MULTILINE | re.DOTALL
        )

        if len(source_files) > 1 or len(target_files) > 1:
            raise UnidiffParseError(
                f"Multiple source and target files found: {diff_text}"
            )
        if not source_files or not target_files:
            raise UnidiffParseError("Invalid diff: missing source or target header")

        return cls(
            diff=diff_text, source_file=source_files[0], target_file=target_files[0]
        )

    @staticmethod
    def _normalize_path(path: str) -> str:
        if path.startswith("a/") or path.startswith("b/"):
            return path[2:]
        return path

    @property
    def is_rename(self) -> bool:
        if self.source_file == DEV_NULL or self.target_file == DEV_NULL:
            return False
        return self._normalize_path(self.source_file) != self._normalize_path(
            self.target_file
        )

    @property
    def is_added_file(self) -> bool:
        return self.source_file == DEV_NULL

    @property
    def is_removed_file(self) -> bool:
        return self.target_file == DEV_NULL

    @property
    def is_modified_file(self) -> bool:
        return not (self.is_added_file or self.is_removed_file)

    @property
    def old_path(self) -> str | None:
        if self.is_added_file:
            return None
        return self._normalize_path(self.source_file)

    @property
    def new_path(self) -> str | None:
        if self.is_removed_file:
            return None
        return self._normalize_path(self.target_file)

    @property
    def path(self) -> str:
        filepath = self.source_file
        if filepath in (None, DEV_NULL) or (
            self.is_rename and self.target_file not in (None, DEV_NULL)
        ):
            filepath = self.target_file

        if not filepath or filepath == DEV_NULL:
            raise UnidiffParseError("Invalid diff: could not determine file path")

        return self._normalize_path(filepath)


class UDiffRepresentationExtractor(PatchRepresentationExtractor):
    @staticmethod
    def _count_diff_lines(diff_text: str) -> tuple[int, int]:
        additions = 0
        deletions = 0
        for line in diff_text.splitlines():
            if line.startswith("+++ ") or line.startswith("--- "):
                continue
            if line.startswith("+"):
                additions += 1
            elif line.startswith("-"):
                deletions += 1
        return additions, deletions

    @staticmethod
    def _split_multi_file_udiff(raw_text: str) -> list[str]:
        raw_text = raw_text.strip("\n")
        if not raw_text:
            return []

        lines = raw_text.splitlines(keepends=True)
        starts: list[int] = [
            idx for idx, line in enumerate(lines) if line.startswith("--- ")
        ]
        if not starts:
            return [raw_text]

        chunks: list[str] = []
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(lines)
            chunk = "".join(lines[start:end]).strip("\n")
            if chunk:
                chunks.append(chunk)
        return chunks

    def extract(self, raw_text: str) -> list[ParsedPatch]:
        diffs = self._split_multi_file_udiff(raw_text)
        parsed_items: list[ParsedPatch] = []

        for diff_text in diffs:
            parsed = ParsedDiffPatch.from_text(diff_text)

            if parsed.is_added_file:
                operation = ParsedPatchOperation.ADD
            elif parsed.is_removed_file:
                operation = ParsedPatchOperation.DELETE
            elif parsed.is_rename:
                operation = ParsedPatchOperation.RENAME
            else:
                operation = ParsedPatchOperation.MODIFY

            additions, deletions = self._count_diff_lines(parsed.diff)
            patch = ParsedPatch(
                diff=parsed.diff,
                old_path=parsed.old_path,
                new_path=parsed.new_path,
                operation=operation,
                is_rename=parsed.is_rename,
                is_added_file=parsed.is_added_file,
                is_removed_file=parsed.is_removed_file,
                is_modified_file=parsed.is_modified_file,
                path=parsed.path,
                additions=additions,
                deletions=deletions,
            )

            parsed_items.append(patch)

        return parsed_items
