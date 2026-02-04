"""Tests for coder single-shot patching."""

from unittest.mock import ANY, AsyncMock, MagicMock

from app.coder.schemas import (
    SingleShotDiffAppliedEvent,
)
from app.patches.enums import DiffPatchStatus


class TestSingleShotPatchService:
    async def test_apply_from_blocks_delegates_to_extract_diffs_from_blocks(
        self, single_shot_patch_service
    ):
        """Should call DiffPatchService.extract_diffs_from_blocks(turn_id, session_id, blocks, processor_type)."""
        mock_diff_service = MagicMock()
        mock_diff_service.extract_diffs_from_blocks.return_value = []
        mock_diff_service.process_diff = AsyncMock()
        async def _diff_patch_service_factory():
            return mock_diff_service

        single_shot_patch_service.diff_patch_service_factory = _diff_patch_service_factory

        blocks = [{"type": "tool"}]
        async for _ in single_shot_patch_service.apply_from_blocks(
            session_id=1, turn_id="t1", blocks=blocks
        ):
            # Exhaust generator
            _ = _

        mock_diff_service.extract_diffs_from_blocks.assert_called_with(
            turn_id="t1", session_id=1, blocks=blocks, processor_type=ANY
        )

    async def test_apply_from_blocks_yields_applied_event_per_patch_in_representation(
        self, single_shot_patch_service
    ):
        """When process_diff returns APPLIED with representation.patches, yield SingleShotDiffAppliedEvent per patch."""
        mock_diff_service = MagicMock()
        mock_patch = MagicMock()
        mock_patch.path = "file.py"
        mock_rep = MagicMock()
        mock_rep.patches = [mock_patch]

        mock_result = MagicMock()
        mock_result.status = DiffPatchStatus.APPLIED
        mock_result.representation = mock_rep

        mock_diff_service.extract_diffs_from_blocks.return_value = ["diff1"]
        mock_diff_service.process_diff = AsyncMock(return_value=mock_result)
        async def _diff_patch_service_factory():
            return mock_diff_service

        single_shot_patch_service.diff_patch_service_factory = _diff_patch_service_factory

        # Mock context service to avoid failure later
        context_service = AsyncMock()
        context_service.get_active_context = AsyncMock(return_value=[])
        async def _context_service_factory(_session):  # noqa: ANN001
            return context_service

        single_shot_patch_service.context_service_factory = _context_service_factory

        events = [
            e
            async for e in single_shot_patch_service.apply_from_blocks(
                session_id=1, turn_id="t1", blocks=[]
            )
        ]

        assert isinstance(events[0], SingleShotDiffAppliedEvent)
        assert events[0].file_path == "file.py"

    async def test_apply_from_blocks_skips_when_process_diff_not_applied(
        self, single_shot_patch_service
    ):
        """Should not yield SingleShotDiffAppliedEvent when status != APPLIED."""
        mock_diff_service = MagicMock()
        mock_result = MagicMock()
        mock_result.status = DiffPatchStatus.FAILED
        mock_diff_service.extract_diffs_from_blocks.return_value = ["diff1"]
        mock_diff_service.process_diff = AsyncMock(return_value=mock_result)
        async def _diff_patch_service_factory():
            return mock_diff_service

        single_shot_patch_service.diff_patch_service_factory = _diff_patch_service_factory

        events = [
            e
            async for e in single_shot_patch_service.apply_from_blocks(
                session_id=1, turn_id="t1", blocks=[]
            )
        ]

        assert len(events) == 0

    async def test_apply_from_blocks_skips_when_representation_missing_or_empty(
        self, single_shot_patch_service
    ):
        """Should not yield applied events when representation is None or has no patches."""
        mock_diff_service = MagicMock()
        mock_result = MagicMock()
        mock_result.status = DiffPatchStatus.APPLIED
        mock_result.representation = None  # Empty
        mock_diff_service.extract_diffs_from_blocks.return_value = ["diff1"]
        mock_diff_service.process_diff = AsyncMock(return_value=mock_result)
        async def _diff_patch_service_factory():
            return mock_diff_service

        single_shot_patch_service.diff_patch_service_factory = _diff_patch_service_factory

        events = [
            e
            async for e in single_shot_patch_service.apply_from_blocks(
                session_id=1, turn_id="t1", blocks=[]
            )
        ]

        assert len(events) == 0

    async def test_apply_from_blocks_syncs_context_only_for_add_remove_rename(
        self, single_shot_patch_service
    ):
        """Should call context_service.sync_context_for_diff only for add/remove/rename patches."""

        mock_diff_service = MagicMock()

        patch_apply = MagicMock()
        patch_apply.path = "added.py"
        patch_apply.is_added_file = True
        patch_apply.is_removed_file = False
        patch_apply.is_rename = False

        patch_skip = MagicMock()
        patch_skip.path = "updated.py"
        patch_skip.is_added_file = False
        patch_skip.is_removed_file = False
        patch_skip.is_rename = False

        rep = MagicMock()
        rep.patches = [patch_apply, patch_skip]

        result = MagicMock()
        result.status = DiffPatchStatus.APPLIED
        result.representation = rep

        mock_diff_service.extract_diffs_from_blocks.return_value = ["diff1"]
        mock_diff_service.process_diff = AsyncMock(return_value=result)

        async def _diff_patch_service_factory():
            return mock_diff_service

        single_shot_patch_service.diff_patch_service_factory = _diff_patch_service_factory

        context_service = AsyncMock()
        context_service.sync_context_for_diff = AsyncMock(return_value=None)
        context_service.get_active_context = AsyncMock(return_value=[])

        async def _context_service_factory(_session):  # noqa: ANN001
            return context_service

        single_shot_patch_service.context_service_factory = _context_service_factory

        _ = [
            e
            async for e in single_shot_patch_service.apply_from_blocks(
                session_id=1, turn_id="t1", blocks=[]
            )
        ]

        assert context_service.sync_context_for_diff.await_count == 1

    async def test_apply_from_blocks_yields_workflow_log_error_when_context_sync_fails(
        self, single_shot_patch_service
    ):
        """If sync_context_for_diff raises, yield WorkflowLogEvent(level=ERROR) and continue."""
        from app.coder.schemas import LogLevel, WorkflowLogEvent

        mock_diff_service = MagicMock()
        patch_apply = MagicMock()
        patch_apply.path = "added.py"
        patch_apply.is_added_file = True
        patch_apply.is_removed_file = False
        patch_apply.is_rename = False

        rep = MagicMock()
        rep.patches = [patch_apply]

        result = MagicMock()
        result.status = DiffPatchStatus.APPLIED
        result.representation = rep

        mock_diff_service.extract_diffs_from_blocks.return_value = ["diff1"]
        mock_diff_service.process_diff = AsyncMock(return_value=result)

        async def _diff_patch_service_factory():
            return mock_diff_service

        single_shot_patch_service.diff_patch_service_factory = _diff_patch_service_factory

        context_service = AsyncMock()
        context_service.sync_context_for_diff = AsyncMock(side_effect=Exception("nope"))
        context_service.get_active_context = AsyncMock(return_value=[])

        async def _context_service_factory(_session):  # noqa: ANN001
            return context_service

        single_shot_patch_service.context_service_factory = _context_service_factory

        events = [
            e
            async for e in single_shot_patch_service.apply_from_blocks(
                session_id=1, turn_id="t1", blocks=[]
            )
        ]

        assert any(
            isinstance(e, WorkflowLogEvent) and e.level == LogLevel.ERROR
            for e in events
        )

    async def test_apply_from_blocks_yields_context_files_updated_event_at_end(
        self, single_shot_patch_service
    ):
        """Should yield ContextFilesUpdatedEvent with ContextFileListItem for active context."""
        from app.coder.schemas import ContextFilesUpdatedEvent
        from app.context.schemas import ContextFileListItem

        mock_diff_service = MagicMock()
        patch_apply = MagicMock()
        patch_apply.is_added_file = True
        patch_apply.is_removed_file = False
        patch_apply.is_rename = False
        patch_apply.path = "file.py"

        rep = MagicMock()
        rep.patches = [patch_apply]

        result = MagicMock()
        result.status = DiffPatchStatus.APPLIED
        result.representation = rep

        mock_diff_service.extract_diffs_from_blocks.return_value = ["diff1"]
        mock_diff_service.process_diff = AsyncMock(return_value=result)

        async def _diff_patch_service_factory():
            return mock_diff_service

        single_shot_patch_service.diff_patch_service_factory = _diff_patch_service_factory

        # Active context list (service expects ORM-ish objects with id + file_path)
        file_obj = MagicMock()
        file_obj.id = 1
        file_obj.file_path = "file.py"

        context_service = AsyncMock()
        context_service.sync_context_for_diff = AsyncMock(return_value=None)
        context_service.get_active_context = AsyncMock(return_value=[file_obj])

        async def _context_service_factory(_session):  # noqa: ANN001
            return context_service

        single_shot_patch_service.context_service_factory = _context_service_factory

        events = [
            e
            async for e in single_shot_patch_service.apply_from_blocks(
                session_id=1, turn_id="t1", blocks=[]
            )
        ]

        last = events[-1]
        assert isinstance(last, ContextFilesUpdatedEvent)
        assert last.files == [ContextFileListItem(id=1, file_path="file.py")]

    async def test_apply_from_blocks_returns_early_when_no_representations_applied(
        self, single_shot_patch_service
    ):
        """Should yield nothing (no ContextFilesUpdatedEvent) when no diffs were applied."""
        mock_diff_service = MagicMock()
        mock_diff_service.extract_diffs_from_blocks.return_value = []  # No diffs
        mock_diff_service.process_diff = AsyncMock()
        async def _diff_patch_service_factory():
            return mock_diff_service

        single_shot_patch_service.diff_patch_service_factory = _diff_patch_service_factory

        events = [
            e
            async for e in single_shot_patch_service.apply_from_blocks(
                session_id=1, turn_id="t1", blocks=[]
            )
        ]

        assert len(events) == 0
