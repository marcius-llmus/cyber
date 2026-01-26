"""Tooling tests for patches (PatcherTools)."""


class TestPatcherToolsToToolList:
    def test_to_tool_list_uses_udiff_metadata_by_default(self, mocker, patcher_tools):
        """Should build ToolMetadata with UDIFF schema/description and pass mapping to BaseToolSet."""
        pass

    def test_to_tool_list_passes_metadata_mapping_into_super_to_tool_list(
        self, mocker, patcher_tools
    ):
        """Should call BaseToolSet.to_tool_list(..., func_to_metadata_mapping={...})."""
        pass

    def test_to_tool_list_raises_for_invalid_processor_type(self, mocker, patcher_tools):
        """Should raise RuntimeError if _get_patch_processor_type_from_settings returns unknown type."""
        pass

    def test_build_apply_patch_metadata_builds_pydantic_schema_with_patch_field(self):
        """Schema should include a 'patch' field and descriptions should vary by processor type."""
        pass


class TestPatcherToolsFormatSaveResult:
    def test_format_save_result_applied(self):
        """Should format APPLIED result including patch_id."""
        pass

    def test_format_save_result_failed_includes_error(self):
        """Should format FAILED result including error_message fallback."""
        pass

    def test_format_save_result_pending(self):
        """Should format PENDING as saved-but-not-applied message."""
        pass

    def test_format_save_result_raises_for_unknown_status(self):
        """Should raise NotImplementedError for unsupported DiffPatchStatus."""
        pass


class TestPatcherToolsApplyPatch:
    async def test_apply_patch_returns_error_when_session_id_missing(self, patcher_tools):
        """Should return user-safe error string when tool has no session_id."""
        pass

    async def test_apply_patch_returns_error_when_turn_id_missing(self, patcher_tools):
        """Should return user-safe error string when tool has no turn_id."""
        pass

    async def test_apply_patch_calls_service_process_diff_and_formats_result(
        self, mocker, patcher_tools
    ):
        """Should await build_diff_patch_service, then process_diff with DiffPatchCreate, then format."""
        pass

    async def test_apply_patch_uses_processor_type_from_settings(self, mocker, patcher_tools):
        """Should use _get_patch_processor_type_from_settings() and include it in DiffPatchCreate."""
        pass

    async def test_apply_patch_passes_through_internal_tool_call_id_requirement(self, mocker):
        """CustomFunctionTool enforces internal_tool_call_id; apply_patch signature includes it."""
        pass

    async def test_apply_patch_catches_and_formats_unexpected_error(
        self, mocker, patcher_tools
    ):
        """Should catch exception and return 'Error saving/applying patch: ...'."""
        pass

    async def test_apply_patch_returns_error_string_when_service_process_diff_raises(self, mocker):
        """Should catch service exceptions and return safe error string."""
        pass