"""Schema tests for the patches app."""

import pytest


class TestPatchRepresentation:
    def test_from_text_routes_to_extractor_by_processor_type(self):
        """Should select extractor based on PatchProcessorType and return PatchRepresentation."""
        pass

    def test_from_text_raises_for_unknown_processor_type(self):
        """Should raise NotImplementedError for unsupported processor types."""
        pass


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
        pass

    def test_extract_splits_multi_file_udiff(self):
        """Should split text containing multiple '--- ' headers into multiple ParsedPatch entries."""
        pass

    def test_extract_counts_additions_and_deletions(self):
        """Should compute additions/deletions excluding ---/+++ headers."""
        pass


class TestParsedDiffPatch:
    def test_from_text_raises_for_missing_headers(self):
        """Should raise UnidiffParseError if ---/+++ headers are missing."""
        pass
