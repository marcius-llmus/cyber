import pytest
from apply_patch_py.models import AddFile, DeleteFile, UpdateFile, UpdateFileChunk

from app.patches.enums import ParsedPatchOperation, PatchProcessorType
from app.patches.schemas import (
    CodexPatchRepresentationExtractor,
    PatchRepresentation,
    UDiffRepresentationExtractor,
    UnidiffParseError,
)
from app.patches.schemas.udiff import DEV_NULL, ParsedDiffPatch


class TestCodexPatchRepresentationExtractor:
    def test_extract_parses_add_file_hunk(self, mocker):
        """Should return ParsedPatch(operation=ADD) and count additions from content lines."""

        class _FakePatch:
            def __init__(self, hunks):
                self.hunks = hunks

        extractor = CodexPatchRepresentationExtractor()
        raw_text = "RAW"
        hunk = AddFile(path="a.txt", content="hello\nworld\n")

        mocker.patch(
            "app.patches.schemas.codex.PatchParser.parse",
            return_value=_FakePatch([hunk]),
        )
        patches = extractor.extract(raw_text)

        assert len(patches) == 1
        assert patches[0].operation == ParsedPatchOperation.ADD
        assert patches[0].is_added_file is True
        assert patches[0].path == "a.txt"
        assert patches[0].additions == 2
        assert patches[0].deletions == 0

    def test_extract_parses_delete_file_hunk(self, mocker):
        """Should return ParsedPatch(operation=DELETE) when PatchParser yields DeleteFile."""

        class _FakePatch:
            def __init__(self, hunks):
                self.hunks = hunks

        extractor = CodexPatchRepresentationExtractor()
        raw_text = "RAW"
        hunk = DeleteFile(path="a.txt")

        mocker.patch(
            "app.patches.schemas.codex.PatchParser.parse",
            return_value=_FakePatch([hunk]),
        )
        patches = extractor.extract(raw_text)

        assert len(patches) == 1
        assert patches[0].operation == ParsedPatchOperation.DELETE
        assert patches[0].is_removed_file is True
        assert patches[0].path == "a.txt"
        assert patches[0].additions == 0
        assert patches[0].deletions == 0

    def test_extract_parses_update_file_modify_hunk(self, mocker):
        """Should return ParsedPatch(operation=MODIFY) and count added/removed lines from chunks."""

        class _FakePatch:
            def __init__(self, hunks):
                self.hunks = hunks

        extractor = CodexPatchRepresentationExtractor()
        raw_text = "RAW"
        # 1 unchanged line, 1 removed line, 2 added lines
        chunk = UpdateFileChunk(
            diff="@@\n same\n-old\n+new\n+new2\n",
            old_lines=["same", "old"],
            new_lines=["same", "new", "new2"],
        )
        hunk = UpdateFile(path="a.txt", chunks=[chunk])

        mocker.patch(
            "app.patches.schemas.codex.PatchParser.parse",
            return_value=_FakePatch([hunk]),
        )
        patches = extractor.extract(raw_text)

        assert len(patches) == 1
        assert patches[0].operation == ParsedPatchOperation.MODIFY
        assert patches[0].is_modified_file is True
        assert patches[0].is_rename is False
        assert patches[0].path == "a.txt"
        assert patches[0].additions == 2
        assert patches[0].deletions == 1

    def test_extract_parses_update_file_rename_hunk(self, mocker):
        """Should return ParsedPatch(operation=RENAME) and count added/removed lines from chunks."""

        class _FakePatch:
            def __init__(self, hunks):
                self.hunks = hunks

        extractor = CodexPatchRepresentationExtractor()
        raw_text = "RAW"
        chunk = UpdateFileChunk(
            diff="@@\n same\n-old\n+new\n",
            old_lines=["same", "old"],
            new_lines=["same", "new"],
        )
        hunk = UpdateFile(path="a.txt", chunks=[chunk], move_to="b.txt")

        mocker.patch(
            "app.patches.schemas.codex.PatchParser.parse",
            return_value=_FakePatch([hunk]),
        )
        patches = extractor.extract(raw_text)

        assert len(patches) == 1
        assert patches[0].operation == ParsedPatchOperation.RENAME
        assert patches[0].is_rename is True
        assert patches[0].path == "b.txt"
        assert patches[0].old_path == "a.txt"
        assert patches[0].new_path == "b.txt"
        assert patches[0].additions == 1
        assert patches[0].deletions == 1

    def test_extract_raises_for_unsupported_hunk_type(self, mocker):
        """Should raise ValueError for unexpected hunk classes."""

        class _Unsupported:  # noqa: N801
            pass

        class _FakePatch:
            def __init__(self, hunks):
                self.hunks = hunks

        extractor = CodexPatchRepresentationExtractor()

        mocker.patch(
            "app.patches.schemas.codex.PatchParser.parse",
            return_value=_FakePatch([_Unsupported()]),
        )

        with pytest.raises(ValueError, match="Unsupported codex patch hunk type"):
            extractor.extract("RAW")

    def test_extract_parses_add_file_hunk_counts_blank_lines(self, mocker):
        class _FakePatch:
            def __init__(self, hunks):
                self.hunks = hunks

        extractor = CodexPatchRepresentationExtractor()
        hunk = AddFile(path="a.txt", content="a\n\nB\n")

        mocker.patch(
            "app.patches.schemas.codex.PatchParser.parse",
            return_value=_FakePatch([hunk]),
        )

        patches = extractor.extract("RAW")
        assert patches[0].additions == 3
        assert patches[0].deletions == 0

    def test_extract_parses_delete_file_hunk_counts_zero(self, mocker):
        class _FakePatch:
            def __init__(self, hunks):
                self.hunks = hunks

        extractor = CodexPatchRepresentationExtractor()
        hunk = DeleteFile(path="a.txt")

        mocker.patch(
            "app.patches.schemas.codex.PatchParser.parse",
            return_value=_FakePatch([hunk]),
        )

        patches = extractor.extract("RAW")
        assert patches[0].additions == 0
        assert patches[0].deletions == 0


class TestPatchRepresentation:
    def test_from_text_routes_to_extractor_by_processor_type(self):
        """Should select extractor based on PatchProcessorType and return PatchRepresentation."""
        raw = "--- /dev/null\n+++ b/a.txt\n@@ -0,0 +1,1 @@\n+hi\n"
        rep = PatchRepresentation.from_text(
            raw_text=raw, processor_type=PatchProcessorType.UDIFF_LLM
        )
        assert rep.processor_type == PatchProcessorType.UDIFF_LLM
        assert len(rep.patches) == 1
        assert rep.patches[0].additions == 1
        assert rep.patches[0].deletions == 0

    def test_from_text_routes_to_codex_extractor_and_counts(self, mocker):
        """Should select Codex extractor and populate additions/deletions based on codex hunks."""

        class _FakePatch:
            def __init__(self, hunks):
                self.hunks = hunks

        raw_text = (
            "*** Begin Patch\n*** Update File: a.txt\n@@\n-hello\n+hi\n*** End Patch"
        )
        chunk = UpdateFileChunk(
            diff="@@\n-hello\n+hi\n", old_lines=["hello"], new_lines=["hi"]
        )
        hunk = UpdateFile(path="a.txt", chunks=[chunk])
        mocker.patch(
            "app.patches.schemas.codex.PatchParser.parse",
            return_value=_FakePatch([hunk]),
        )

        rep = PatchRepresentation.from_text(
            raw_text=raw_text, processor_type=PatchProcessorType.CODEX_APPLY
        )
        assert rep.processor_type == PatchProcessorType.CODEX_APPLY
        assert len(rep.patches) == 1
        assert rep.patches[0].additions == 1
        assert rep.patches[0].deletions == 1

    def test_has_changes_true_when_patches_present(self):
        """Should return True when representation.patches is non-empty."""
        rep = PatchRepresentation(
            processor_type=PatchProcessorType.UDIFF_LLM,
            patches=[
                UDiffRepresentationExtractor().extract(
                    "--- /dev/null\n+++ b/a.txt\n@@ -0,0 +1,1 @@\n+hi\n"
                )[0]
            ],
        )
        assert rep.has_changes is True

    def test_has_changes_false_when_no_patches(self):
        """Should return False when representation.patches is empty."""
        rep = PatchRepresentation(
            processor_type=PatchProcessorType.UDIFF_LLM, patches=[]
        )
        assert rep.has_changes is False

    def test_from_text_raises_for_unknown_processor_type(self):
        """Should raise NotImplementedError for unsupported processor types."""
        with pytest.raises(NotImplementedError, match="Unknown PatchProcessorType"):
            PatchRepresentation.from_text(raw_text="x", processor_type="NOPE")  # type: ignore[arg-type]


class TestUDiffRepresentationExtractor:
    @pytest.mark.parametrize(
        "diff_text, expected_operation",
        [
            ("--- /dev/null\n+++ b/a.txt\n@@ -0,0 +1,1 @@\n+hi\n", "ADD"),
            ("--- a/a.txt\n+++ /dev/null\n@@ -1,1 +0,0 @@\n-hi\n", "DELETE"),
            (
                "--- a/a.txt\n+++ b/a.txt\n@@ -1,1 +1,1 @@\n-hi\n+hello\n",
                "MODIFY",
            ),
            (
                "--- a/a.txt\n+++ b/b.txt\n@@ -1,1 +1,1 @@\n-hi\n+hello\n",
                "RENAME",
            ),
        ],
    )
    def test_extract_sets_operation_flags_and_path(self, diff_text, expected_operation):
        """Should compute operation/is_* flags and normalized path."""
        extractor = UDiffRepresentationExtractor()
        items = extractor.extract(diff_text)
        assert len(items) == 1
        patch = items[0]
        assert patch.operation.value == expected_operation
        assert patch.path in ("a.txt", "b.txt")

        if expected_operation == "ADD":
            assert patch.is_added_file is True
            assert patch.old_path is None
            assert patch.new_path == "a.txt"
        if expected_operation == "DELETE":
            assert patch.is_removed_file is True
            assert patch.old_path == "a.txt"
            assert patch.new_path is None
        if expected_operation == "RENAME":
            assert patch.is_rename is True

    def test_extract_splits_multi_file_udiff(self):
        """Should split text containing multiple '--- ' headers into multiple ParsedPatch entries."""
        raw = (
            "--- a/a.txt\n+++ b/a.txt\n@@ -1,1 +1,1 @@\n-hi\n+hello\n\n"
            "--- a/b.txt\n+++ b/b.txt\n@@ -1,1 +1,1 @@\n-hi\n+hello\n"
        )
        items = UDiffRepresentationExtractor().extract(raw)
        assert len(items) == 2
        assert {p.path for p in items} == {"a.txt", "b.txt"}

    def test_split_multi_file_udiff_returns_empty_for_blank_text(self):
        """Should return [] when raw_text is empty or only newlines."""
        extractor = UDiffRepresentationExtractor()
        assert extractor._split_multi_file_udiff("") == []  # noqa: SLF001
        assert extractor._split_multi_file_udiff("\n\n") == []  # noqa: SLF001

    def test_count_diff_lines_ignores_headers(self):
        """Should not count ---/+++ header lines as deletions/additions."""
        extractor = UDiffRepresentationExtractor()
        adds, dels = extractor._count_diff_lines(
            "--- a/a.txt\n+++ b/a.txt\n+hi\n-bye\n"
        )  # noqa: SLF001
        assert adds == 1
        assert dels == 1

    def test_extract_counts_additions_and_deletions(self):
        """Should compute additions/deletions excluding ---/+++ headers."""
        raw = "--- a/a.txt\n+++ b/a.txt\n@@ -1,1 +1,2 @@\n-hi\n+hello\n+world\n"
        patch = UDiffRepresentationExtractor().extract(raw)[0]
        assert patch.additions == 2
        assert patch.deletions == 1

    def test_extract_allows_leading_noise_before_first_header(self):
        """Should ignore any prelude text before first '--- ' and still parse diffs."""
        raw = "noise line\n" "--- a/a.txt\n+++ b/a.txt\n@@ -1,1 +1,1 @@\n-hi\n+hello\n"
        patch = UDiffRepresentationExtractor().extract(raw)[0]
        assert patch.path == "a.txt"


class TestParsedDiffPatch:
    def test_from_text_raises_for_missing_headers(self):
        """Should raise UnidiffParseError if ---/+++ headers are missing."""
        with pytest.raises(UnidiffParseError, match="missing source or target header"):
            ParsedDiffPatch.from_text("@@ -1 +1 @@\n-hi\n+hello\n")

    def test_from_text_raises_for_multiple_headers(self):
        """Should raise UnidiffParseError when multiple source/target headers are present."""
        raw = (
            "--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-hi\n+hello\n"
            "--- a/b.txt\n+++ b/b.txt\n@@ -1 +1 @@\n-hi\n+hello\n"
        )
        with pytest.raises(UnidiffParseError, match="Multiple source and target files"):
            ParsedDiffPatch.from_text(raw)

    def test_path_prefers_target_on_rename(self):
        """Should choose target_file path when diff represents a rename."""
        raw = "--- a/a.txt\n+++ b/b.txt\n@@ -1,1 +1,1 @@\n-hi\n+hello\n"
        parsed = ParsedDiffPatch.from_text(raw)
        assert parsed.is_rename is True
        assert parsed.path == "b.txt"

    def test_path_raises_when_cannot_determine_path(self):
        """Should raise UnidiffParseError if path is /dev/null or missing."""
        raw = f"--- {DEV_NULL}\n+++ {DEV_NULL}\n"
        parsed = ParsedDiffPatch.from_text(raw)
        with pytest.raises(UnidiffParseError, match="could not determine file path"):
            _ = parsed.path

    def test_from_text_accepts_headers_with_timestamps(self):
        """Should parse headers with tab-separated timestamps (standard unified diff)."""
        raw = (
            "--- a/a.txt\t2020-01-01 00:00:00\n"
            "+++ b/a.txt\t2020-01-01 00:00:00\n"
            "@@ -1,1 +1,1 @@\n-hi\n+hello\n"
        )
        parsed = ParsedDiffPatch.from_text(raw)
        assert parsed.old_path == "a.txt"
        assert parsed.new_path == "a.txt"
