"""Service tests for the patches app."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.patches.enums import DiffPatchStatus, PatchProcessorType
from app.patches.schemas import DiffPatchApplyPatchResult, DiffPatchCreate
from app.patches.services import DiffPatchService
from app.patches.services.processors.udiff_processor import UDiffProcessor


class TestDiffPatchService:
    def test_extract_diffs_from_blocks_extracts_only_diff_fenced_blocks(self):
        """Should parse ```diff fenced blocks from concatenated text blocks."""
        service = DiffPatchService(
            db=AsyncMock(),
            diff_patch_repo_factory=lambda _db: AsyncMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        blocks = [
            {"type": "text", "content": "hello\n```diff\n--- a/a.txt\n+++ b/a.txt\n```\n"},
            {"type": "tool", "content": "ignored"},
        ]
        patches = service.extract_diffs_from_blocks(
            turn_id="t1", session_id=1, blocks=blocks
        )
        assert len(patches) == 1
        assert patches[0].diff.startswith("--- a/a.txt")

    def test_extract_diffs_from_blocks_extracts_multiple_diff_blocks(self):
        """Should return a DiffPatchCreate per fenced diff block (order preserved)."""
        service = DiffPatchService(
            db=AsyncMock(),
            diff_patch_repo_factory=lambda _db: AsyncMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        blocks = [
            {
                "type": "text",
                "content": (
                    "```diff\n--- a/a.txt\n+++ b/a.txt\n```\n"
                    "x\n"
                    "```diff\n--- a/b.txt\n+++ b/b.txt\n```"
                ),
            }
        ]
        patches = service.extract_diffs_from_blocks(
            turn_id="t1", session_id=1, blocks=blocks
        )
        assert [p.diff.splitlines()[0] for p in patches] == ["--- a/a.txt", "--- a/b.txt"]

    def test_extract_diffs_from_blocks_accepts_diffpy_fenced_blocks(self):
        r"""Should parse ```diffpy (and diff*) fenced blocks (regex supports diff(?:\w+)?)."""
        service = DiffPatchService(
            db=AsyncMock(),
            diff_patch_repo_factory=lambda _db: AsyncMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        blocks = [
            {
                "type": "text",
                "content": "```diffpy\n--- a/a.txt\n+++ b/a.txt\n```",
            }
        ]
        patches = service.extract_diffs_from_blocks(
            turn_id="t1", session_id=1, blocks=blocks
        )
        assert len(patches) == 1

    def test_extract_diffs_from_blocks_ignores_non_text_blocks(self):
        """Should ignore tool blocks and only read text blocks."""
        service = DiffPatchService(
            db=AsyncMock(),
            diff_patch_repo_factory=lambda _db: AsyncMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        patches = service.extract_diffs_from_blocks(
            turn_id="t1",
            session_id=1,
            blocks=[{"type": "tool", "content": "```diff\n--- a/a\n+++ b/a\n```"}],
        )
        assert patches == []

    def test_extract_diffs_from_blocks_returns_empty_when_no_text(self):
        """Should return [] if there is no text content."""
        service = DiffPatchService(
            db=AsyncMock(),
            diff_patch_repo_factory=lambda _db: AsyncMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        patches = service.extract_diffs_from_blocks(
            turn_id="t1", session_id=1, blocks=[]
        )
        assert patches == []

    def test_extract_diffs_from_blocks_handles_blocks_none(self):
        """Should return [] when blocks is None."""
        service = DiffPatchService(
            db=AsyncMock(),
            diff_patch_repo_factory=lambda _db: AsyncMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        assert (
            service.extract_diffs_from_blocks(
                turn_id="t1", session_id=1, blocks=None
            )
            == []
        )

    def test_extract_diffs_from_blocks_returns_empty_when_no_diff_blocks(self):
        """Should return [] when text has no fenced diff blocks."""
        service = DiffPatchService(
            db=AsyncMock(),
            diff_patch_repo_factory=lambda _db: AsyncMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        blocks = [{"type": "text", "content": "no diff here"}]
        assert (
            service.extract_diffs_from_blocks(turn_id="t1", session_id=1, blocks=blocks)
            == []
        )

    def test_extract_diffs_from_blocks_raises_when_diff_block_is_empty(self):
        """Should raise ValueError for empty fenced diff block content."""
        service = DiffPatchService(
            db=AsyncMock(),
            diff_patch_repo_factory=lambda _db: AsyncMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        blocks = [{"type": "text", "content": "```diff\n\n```"}]
        with pytest.raises(ValueError, match="No content to parse"):
            service.extract_diffs_from_blocks(turn_id="t1", session_id=1, blocks=blocks)

    def test_extract_diff_patches_from_text_requires_closing_fence(self):
        """Should not match unterminated ```diff block (no closing ```), returning []."""
        patches = DiffPatchService._extract_diff_patches_from_text(
            turn_id="t1",
            session_id=1,
            text="```diff\n--- a/a.txt\n+++ b/a.txt\n",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        assert patches == []

    def test_extract_diff_patches_from_text_handles_windows_newlines(self):
        """Should parse diffs when text uses \r\n newlines."""
        text = "```diff\r\n--- a/a.txt\r\n+++ b/a.txt\r\n```"
        patches = DiffPatchService._extract_diff_patches_from_text(
            turn_id="t1",
            session_id=1,
            text=text,
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        assert len(patches) == 1

    def test_extract_diffs_from_blocks_preserves_processor_type(self):
        """Should set processor_type in returned DiffPatchCreate to provided value."""
        service = DiffPatchService(
            db=AsyncMock(),
            diff_patch_repo_factory=lambda _db: AsyncMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        blocks = [{"type": "text", "content": "```diff\n--- a/a.txt\n+++ b/a.txt\n```"}]
        patches = service.extract_diffs_from_blocks(
            turn_id="t1",
            session_id=1,
            blocks=blocks,
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        assert patches[0].processor_type == PatchProcessorType.UDIFF_LLM

    async def test_process_diff_marks_applied_on_success(self, mocker):
        """Should create PENDING then update to APPLIED when processor succeeds."""
        service: DiffPatchService = mocker.MagicMock(spec=DiffPatchService)
        service._create_pending_patch = AsyncMock(return_value=123)
        processor = mocker.MagicMock()
        processor.apply_patch = AsyncMock(return_value=None)
        service._build_processor = mocker.MagicMock(return_value=processor)
        service._update_patch = AsyncMock(return_value=None)

        import app.patches.services.diff_patches as mod

        rep_obj = mod.PatchRepresentation(
            processor_type=PatchProcessorType.UDIFF_LLM,
            patches=[],
        )
        patch_rep_mock = mocker.patch.object(
            mod.PatchRepresentation,
            "from_text",
            return_value=rep_obj,
        )

        payload = DiffPatchCreate(
            session_id=1,
            turn_id="t1",
            diff="--- a/a.txt\n+++ b/a.txt\n",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        real_service = DiffPatchService(
            db=mocker.MagicMock(),
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        # attach mocked internals
        real_service._create_pending_patch = service._create_pending_patch
        real_service._build_processor = service._build_processor
        real_service._update_patch = service._update_patch

        result = await real_service.process_diff(payload)

        assert isinstance(result, DiffPatchApplyPatchResult)
        assert result.patch_id == 123
        assert result.status == DiffPatchStatus.APPLIED
        assert result.representation == rep_obj
        processor.apply_patch.assert_awaited_once_with(payload.diff)
        patch_rep_mock.assert_called_once_with(
            raw_text=payload.diff, processor_type=payload.processor_type
        )
        assert service._update_patch.await_count == 1

    async def test_process_diff_returns_representation_on_success(self, mocker):
        """Should include PatchRepresentation in result on success."""
        processor = mocker.MagicMock()
        processor.apply_patch = AsyncMock(return_value=None)

        import app.patches.services.diff_patches as mod

        rep_obj = mod.PatchRepresentation(
            processor_type=PatchProcessorType.UDIFF_LLM,
            patches=[],
        )
        mocker.patch.object(mod.PatchRepresentation, "from_text", return_value=rep_obj)

        service = DiffPatchService(
            db=mocker.MagicMock(),
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        service._create_pending_patch = AsyncMock(return_value=1)
        service._build_processor = mocker.MagicMock(return_value=processor)
        service._update_patch = AsyncMock(return_value=None)

        payload = DiffPatchCreate(
            session_id=1,
            turn_id="t1",
            diff="--- a/a.txt\n+++ b/a.txt\n",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        result = await service.process_diff(payload)
        assert result.representation == rep_obj

    async def test_process_diff_marks_failed_on_processor_error(self, mocker):
        """Should create PENDING then update to FAILED when processor raises."""
        processor = mocker.MagicMock()
        processor.apply_patch = AsyncMock(side_effect=ValueError("Boom"))

        service = DiffPatchService(
            db=mocker.MagicMock(),
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        service._create_pending_patch = AsyncMock(return_value=5)
        service._build_processor = mocker.MagicMock(return_value=processor)
        service._update_patch = AsyncMock(return_value=None)

        payload = DiffPatchCreate(
            session_id=1,
            turn_id="t1",
            diff="d",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        result = await service.process_diff(payload)
        assert result.status == DiffPatchStatus.FAILED
        assert result.error_message == "Boom"

    async def test_process_diff_does_not_attempt_to_apply_when_build_processor_raises(
        self, mocker
    ):
        """Should mark FAILED and not call processor.apply_patch if _build_processor raises."""
        service = DiffPatchService(
            db=mocker.MagicMock(),
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        service._create_pending_patch = AsyncMock(return_value=5)
        service._build_processor = mocker.MagicMock(side_effect=ValueError("Boom"))
        service._update_patch = AsyncMock(return_value=None)

        payload = DiffPatchCreate(
            session_id=1,
            turn_id="t1",
            diff="d",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        result = await service.process_diff(payload)
        assert result.status == DiffPatchStatus.FAILED
        assert result.error_message == "Boom"

    async def test_process_diff_keeps_representation_none_when_processor_errors_before_parsing(
        self, mocker
    ):
        """Should return representation=None when processor raises before parsing diff."""
        processor = mocker.MagicMock()
        processor.apply_patch = AsyncMock(side_effect=ValueError("Boom"))

        service = DiffPatchService(
            db=mocker.MagicMock(),
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        service._create_pending_patch = AsyncMock(return_value=5)
        service._build_processor = mocker.MagicMock(return_value=processor)
        service._update_patch = AsyncMock(return_value=None)

        payload = DiffPatchCreate(
            session_id=1,
            turn_id="t1",
            diff="d",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        result = await service.process_diff(payload)
        assert result.representation is None

    async def test_process_diff_updates_failed_when_representation_parsing_raises(
        self, mocker
    ):
        """Should set FAILED if PatchRepresentation.from_text raises after apply_patch."""
        processor = mocker.MagicMock()
        processor.apply_patch = AsyncMock(return_value=None)

        import app.patches.services.diff_patches as mod

        mocker.patch.object(
            mod.PatchRepresentation,
            "from_text",
            side_effect=ValueError("Boom"),
        )

        service = DiffPatchService(
            db=mocker.MagicMock(),
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        service._create_pending_patch = AsyncMock(return_value=5)
        service._build_processor = mocker.MagicMock(return_value=processor)
        service._update_patch = AsyncMock(return_value=None)

        payload = DiffPatchCreate(
            session_id=1,
            turn_id="t1",
            diff="d",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        result = await service.process_diff(payload)
        assert result.status == DiffPatchStatus.FAILED
        assert result.error_message == "Boom"

    async def test_process_diff_marks_failed_when_create_pending_patch_raises(
        self, mocker
    ):
        """Should surface/propagate if _create_pending_patch fails before having patch_id."""
        service = DiffPatchService(
            db=mocker.MagicMock(),
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        service._create_pending_patch = AsyncMock(side_effect=ValueError("Boom"))

        payload = DiffPatchCreate(
            session_id=1,
            turn_id="t1",
            diff="d",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        with pytest.raises(ValueError, match="Boom"):
            await service.process_diff(payload)

    async def test_process_diff_propagates_update_error_when_patch_not_found(
        self, mocker
    ):
        """Should surface ValueError('DiffPatch X not found') when update cannot find patch row."""
        processor = mocker.MagicMock()
        processor.apply_patch = AsyncMock(side_effect=ValueError("Boom"))

        service = DiffPatchService(
            db=mocker.MagicMock(),
            diff_patch_repo_factory=mocker.MagicMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        service._create_pending_patch = AsyncMock(return_value=55)
        service._build_processor = mocker.MagicMock(return_value=processor)
        service._update_patch = AsyncMock(
            side_effect=ValueError("DiffPatch 55 not found")
        )

        payload = DiffPatchCreate(
            session_id=1,
            turn_id="t1",
            diff="d",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        with pytest.raises(ValueError, match="DiffPatch 55 not found"):
            await service.process_diff(payload)

    def test_build_processor_chooses_udiff(self):
        """Should return UDiffProcessor for UDIFF_LLM."""
        service = DiffPatchService(
            db=AsyncMock(),
            diff_patch_repo_factory=lambda _db: AsyncMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        processor = service._build_processor(PatchProcessorType.UDIFF_LLM)
        assert isinstance(processor, UDiffProcessor)

    def test_build_processor_raises_for_codex_until_implemented(self):
        """Should raise NotImplementedError for CODEX_APPLY."""
        service = DiffPatchService(
            db=AsyncMock(),
            diff_patch_repo_factory=lambda _db: AsyncMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        with pytest.raises(NotImplementedError, match="CODEX_APPLY"):
            service._build_processor(PatchProcessorType.CODEX_APPLY)

    def test_build_processor_raises_for_unknown_processor_type(self):
        """Should raise NotImplementedError for unknown PatchProcessorType."""
        service = DiffPatchService(
            db=AsyncMock(),
            diff_patch_repo_factory=lambda _db: AsyncMock(),
            llm_service_factory=AsyncMock(),
            project_service_factory=AsyncMock(),
            codebase_service_factory=AsyncMock(),
        )
        with pytest.raises(NotImplementedError, match="Unknown PatchProcessorType"):
            service._build_processor("NOPE")  # type: ignore[arg-type]