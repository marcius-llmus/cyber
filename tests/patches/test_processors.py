"""Processor tests for the patches app."""


class TestUDiffProcessor:
    def test_strip_markdown_strips_fenced_code_block(self):
        """Should return inner content when response is wrapped in ```...``` fences."""
        pass

    def test_strip_markdown_returns_original_when_not_fenced(self):
        """Should return input text unchanged if no wrapping fences exist."""
        pass
