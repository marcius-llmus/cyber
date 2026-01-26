"""Service tests for the patches app."""


class TestDiffPatchService:
    def test_extract_diffs_from_blocks_extracts_only_diff_fenced_blocks(self):
        """Should parse ```diff fenced blocks from concatenated text blocks."""
        pass

    def test_extract_diffs_from_blocks_ignores_non_text_blocks(self):
        """Should ignore tool blocks and only read text blocks."""
        pass

    def test_extract_diffs_from_blocks_returns_empty_when_no_text(self):
        """Should return [] if there is no text content."""
        pass

    def test_extract_diffs_from_blocks_raises_when_diff_block_is_empty(self):
        """Should raise ValueError for empty fenced diff block content."""
        pass

    async def test_process_diff_marks_applied_on_success(self, mocker):
        """Should create PENDING then update to APPLIED when processor succeeds."""
        pass

    async def test_process_diff_marks_failed_on_processor_error(self, mocker):
        """Should create PENDING then update to FAILED when processor raises."""
        pass

    def test_build_processor_chooses_udiff(self):
        """Should return UDiffProcessor for UDIFF_LLM."""
        pass

    def test_build_processor_raises_for_codex_until_implemented(self):
        """Should raise NotImplementedError for CODEX_APPLY."""
        pass
