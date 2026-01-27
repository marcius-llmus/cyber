from unittest.mock import AsyncMock

import pytest

from app.patches.enums import DiffPatchStatus, PatchProcessorType
from app.patches.schemas import DiffPatchCreate
from app.patches.tools import PatcherTools, _build_apply_patch_metadata


class TestPatcherToolsToToolList:
    def test_to_tool_list_uses_udiff_metadata_by_default(self, mocker, patcher_tools):
        """Should build ToolMetadata with UDIFF schema/description and pass mapping to BaseToolSet."""
        super_mock = mocker.patch(
            "app.commons.tools.BaseToolSet.to_tool_list",
            return_value=["x"],
        )
        out = patcher_tools.to_tool_list()
        assert out == ["x"]

        mapping = super_mock.call_args.kwargs["func_to_metadata_mapping"]
        assert "apply_patch" in mapping
        assert mapping["apply_patch"].name == "apply_patch"

    def test_to_tool_list_passes_metadata_mapping_into_super_to_tool_list(
        self, mocker, patcher_tools
    ):
        """Should call BaseToolSet.to_tool_list(..., func_to_metadata_mapping={...})."""
        super_mock = mocker.patch(
            "app.commons.tools.BaseToolSet.to_tool_list",
            return_value=["x"],
        )
        patcher_tools.to_tool_list()
        assert "func_to_metadata_mapping" in super_mock.call_args.kwargs

    def test_to_tool_list_raises_for_invalid_processor_type(
        self, mocker, patcher_tools
    ):
        """Should raise RuntimeError if settings_snapshot.diff_patch_processor_type is unknown type."""
        patcher_tools.settings_snapshot.diff_patch_processor_type = "NOPE"  # type: ignore[assignment]
        with pytest.raises(RuntimeError, match="Invalid processor type"):
            patcher_tools.to_tool_list()

    def test_build_apply_patch_metadata_builds_pydantic_schema_with_patch_field(self):
        """Schema should include a 'patch' field and descriptions should vary by processor type."""
        meta = _build_apply_patch_metadata(processor_type=PatchProcessorType.UDIFF_LLM)
        assert meta.name == "apply_patch"
        assert "patch" in meta.fn_schema.model_fields


class TestPatcherToolsFormatSaveResult:
    def test_format_save_result_applied(self):
        """Should format APPLIED result including patch_id."""
        assert (
            PatcherTools._format_save_result(
                patch_id=1,
                status=DiffPatchStatus.APPLIED,
                error_message=None,
            )
            == "Applied patch (patch_id=1)."
        )

    def test_format_save_result_failed_includes_error(self):
        """Should format FAILED result including error_message fallback."""
        assert (
            PatcherTools._format_save_result(
                patch_id=1,
                status=DiffPatchStatus.FAILED,
                error_message="Boom",
            )
            == "Failed to apply patch (patch_id=1): Boom"
        )
        assert (
            PatcherTools._format_save_result(
                patch_id=1,
                status=DiffPatchStatus.FAILED,
                error_message=None,
            )
            == "Failed to apply patch (patch_id=1): Unknown error"
        )

    def test_format_save_result_pending(self):
        """Should format PENDING as saved-but-not-applied message."""
        assert (
            PatcherTools._format_save_result(
                patch_id=1,
                status=DiffPatchStatus.PENDING,
                error_message=None,
            )
            == "Patch saved (patch_id=1). Not applied (status=PENDING)."
        )

    def test_format_save_result_raises_for_unknown_status(self):
        """Should raise NotImplementedError for unsupported DiffPatchStatus."""
        with pytest.raises(NotImplementedError, match="Unhandled DiffPatchStatus"):
            PatcherTools._format_save_result(
                patch_id=1,
                status="NOPE",  # type: ignore[arg-type]
                error_message=None,
            )


class TestPatcherToolsApplyPatch:
    async def test_apply_patch_returns_error_when_session_id_missing(
        self, patcher_tools
    ):
        """Should return user-safe error string when tool has no session_id."""
        patcher_tools.session_id = None
        out = await patcher_tools.apply_patch("p", internal_tool_call_id="x")
        assert out.startswith("Error saving/applying patch: ")
        assert "No active session_id" in out

    async def test_apply_patch_returns_error_when_turn_id_missing(self, patcher_tools):
        """Should return user-safe error string when tool has no turn_id."""
        patcher_tools.turn_id = None
        out = await patcher_tools.apply_patch("p", internal_tool_call_id="x")
        assert out.startswith("Error saving/applying patch: ")
        assert "No active turn_id" in out

    async def test_apply_patch_calls_service_process_diff_and_formats_result(
        self, mocker, patcher_tools
    ):
        """Should await build_diff_patch_service, then process_diff with DiffPatchCreate, then format."""
        diff_patch_service = mocker.MagicMock()
        diff_patch_service.process_diff = AsyncMock(
            return_value=mocker.MagicMock(
                patch_id=1, status=DiffPatchStatus.APPLIED, error_message=None
            )
        )
        build_mock = mocker.patch(
            "app.patches.tools.build_diff_patch_service",
            new=AsyncMock(return_value=diff_patch_service),
        )

        out = await patcher_tools.apply_patch(
            "--- a/a.txt\n+++ b/a.txt\n",
            internal_tool_call_id="x",
        )

        assert out == "Applied patch (patch_id=1)."
        build_mock.assert_awaited_once_with()
        diff_patch_service.process_diff.assert_awaited_once()
        payload = diff_patch_service.process_diff.await_args.args[0]
        assert isinstance(payload, DiffPatchCreate)
        assert payload.session_id == patcher_tools.session_id
        assert payload.turn_id == patcher_tools.turn_id

    async def test_apply_patch_uses_processor_type_from_settings(
        self, mocker, patcher_tools
    ):
        """Should use settings_snapshot.diff_patch_processor_type and include it in DiffPatchCreate."""
        patcher_tools.settings_snapshot.diff_patch_processor_type = (
            PatchProcessorType.UDIFF_LLM
        )
        diff_patch_service = mocker.MagicMock()
        diff_patch_service.process_diff = AsyncMock(
            return_value=mocker.MagicMock(
                patch_id=1, status=DiffPatchStatus.PENDING, error_message=None
            )
        )
        mocker.patch(
            "app.patches.tools.build_diff_patch_service",
            new=AsyncMock(return_value=diff_patch_service),
        )

        await patcher_tools.apply_patch("d", internal_tool_call_id="x")
        payload = diff_patch_service.process_diff.await_args.args[0]
        assert payload.processor_type == PatchProcessorType.UDIFF_LLM

    async def test_apply_patch_passes_through_internal_tool_call_id_requirement(
        self, mocker
    ):
        """CustomFunctionTool enforces internal_tool_call_id; apply_patch signature includes it."""
        assert "internal_tool_call_id" in PatcherTools.apply_patch.__code__.co_varnames

    async def test_apply_patch_catches_and_formats_unexpected_error(
        self, mocker, patcher_tools
    ):
        """Should catch exception and return 'Error saving/applying patch: ...'."""
        patcher_tools.settings_snapshot.diff_patch_processor_type = (
            PatchProcessorType.UDIFF_LLM
        )

        diff_patch_service = mocker.MagicMock()
        diff_patch_service.process_diff = AsyncMock(side_effect=RuntimeError("Boom"))
        mocker.patch(
            "app.patches.tools.build_diff_patch_service",
            new=AsyncMock(return_value=diff_patch_service),
        )

        out = await patcher_tools.apply_patch("d", internal_tool_call_id="x")
        assert out == "Error saving/applying patch: Boom"

    async def test_apply_patch_returns_error_string_when_service_process_diff_raises(
        self, mocker, db_sessionmanager_mock, settings_snapshot
    ):
        """Should catch service exceptions and return safe error string."""
        toolset = PatcherTools(
            db=db_sessionmanager_mock,
            settings_snapshot=settings_snapshot,
        )
        toolset.session_id = 1
        toolset.turn_id = "t"

        diff_patch_service = mocker.MagicMock()
        diff_patch_service.process_diff = AsyncMock(side_effect=ValueError("Boom"))
        mocker.patch(
            "app.patches.tools.build_diff_patch_service",
            new=AsyncMock(return_value=diff_patch_service),
        )

        out = await toolset.apply_patch("d", internal_tool_call_id="x")
        assert out == "Error saving/applying patch: Boom"
