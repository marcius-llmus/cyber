"""Service tests for the agents app."""


class TestWorkflowService:
    def test_get_context_hydrates_existing_context(self):
        """Should hydrate a workflow Context from stored state when a record exists."""

        pass

    def test_get_context_creates_new_context_when_missing(self):
        """Should create a new workflow Context when no stored state exists."""

        pass

    def test_get_context_ignores_empty_state(self):
        """Should create a new workflow Context when the stored state is empty or missing."""

        pass

    def test_get_context_calls_repository_with_session_id(self):
        """get_context should call WorkflowStateRepository.get_by_session_id with the given session_id."""

        pass

    def test_get_context_hydrates_using_context_from_dict(self):
        """get_context should call Context.from_dict(workflow, state) when persisted state exists."""

        pass

    def test_save_context_persists_state(self):
        """Should persist the Context state via the repository."""

        pass

    def test_save_context_calls_repository_with_serialized_context(self):
        """save_context should serialize Context to dict and pass it to the repository."""

        pass

    def test_save_context_does_not_return_value(self):
        """save_context should return None after persistence."""

        pass

    def test_save_context_calls_repository_save_state_once(self):
        """save_context should call WorkflowStateRepository.save_state exactly once per invocation."""

        pass

    def test_save_context_propagates_repository_errors(self):
        """save_context should surface exceptions raised by WorkflowStateRepository.save_state."""

        pass


class TestAgentContextService:
    def test_build_system_prompt_raises_when_no_active_project(self):
        """Should raise ActiveProjectRequiredException when there is no active project."""

        pass

    def test_build_system_prompt_chat_mode_is_minimal(self):
        """CHAT mode should not include repo map, active context, or tool rules."""

        pass

    def test_build_system_prompt_chat_mode_includes_only_identity_and_prompt_structure(self):
        """CHAT mode should include only IDENTITY and PROMPT_STRUCTURE sections."""

        pass

    def test_build_system_prompt_includes_repo_map_and_active_context_in_coding_mode(self):
        """CODING mode should include both the repo map and active context when available."""

        pass

    def test_build_system_prompt_includes_repo_map_in_ask_mode(self):
        """ASK mode should include repo map when available and respect read-only constraints."""

        pass

    def test_build_system_prompt_ask_mode_includes_tool_rules(self):
        """ASK mode should include tool usage rules since read-only tools are available."""

        pass

    def test_build_system_prompt_includes_repo_map_in_planner_mode(self):
        """PLANNER mode should include repo map when available and not require patcher tooling."""

        pass

    def test_build_system_prompt_single_shot_mode_excludes_tool_rules(self):
        """SINGLE_SHOT mode should exclude tool usage rules since no tools are available."""

        pass

    def test_build_system_prompt_single_shot_mode_excludes_rules_section_entirely(self):
        """SINGLE_SHOT mode should omit the <RULES> block entirely."""

        pass

    def test_build_system_prompt_planner_mode_includes_tool_rules(self):
        """PLANNER mode should include tool usage rules since read-only tools are available."""

        pass

    def test_build_system_prompt_single_shot_mode_still_requires_active_project(self):
        """SINGLE_SHOT mode should still require an active project to build the system prompt."""

        pass

    def test_build_system_prompt_includes_guidelines_in_non_chat_modes(self):
        """Non-CHAT modes should include coder behavior guidelines."""

        pass

    def test_build_system_prompt_includes_guidelines_for_each_non_chat_mode(self):
        """ASK/PLANNER/CODING/SINGLE_SHOT should each include the GUIDELINES section."""

        pass

    def test_build_system_prompt_includes_custom_prompts_when_present(self):
        """Non-CHAT modes should embed active prompts XML when prompts exist for the project."""

        pass

    def test_build_system_prompt_excludes_custom_prompts_when_absent(self):
        """Non-CHAT modes should omit CUSTOM_INSTRUCTIONS section when no active prompts exist."""

        pass

    def test_build_system_prompt_omits_active_context_when_no_active_files(self):
        """Non-CHAT modes should omit ACTIVE_CONTEXT when workspace has no active files."""

        pass

    def test_build_system_prompt_omits_repo_map_when_repo_map_service_returns_empty(self):
        """Non-CHAT modes should omit REPOSITORY_MAP section when repo map is unavailable."""

        pass

    def test_build_system_prompt_active_context_filters_non_successful_file_reads(self):
        """Active context builder should only include files that were read successfully."""

        pass

    def test_build_system_prompt_sections_order_is_stable(self):
        """build_system_prompt should produce sections in a stable, predictable order."""

        pass

    def test_build_system_prompt_repo_map_includes_description_comment(self):
        """REPOSITORY_MAP section should include the descriptive HTML comment."""

        pass

    def test_build_system_prompt_active_context_includes_description_comment(self):
        """ACTIVE_CONTEXT section should include the descriptive HTML comment."""

        pass

    def test_build_system_prompt_propagates_repo_map_service_errors(self):
        """build_system_prompt should surface exceptions raised by RepoMapService.generate_repo_map."""

        pass

    def test_build_system_prompt_propagates_workspace_service_errors(self):
        """build_system_prompt should surface exceptions raised by WorkspaceService.get_active_context."""

        pass

    def test_build_system_prompt_propagates_codebase_service_errors(self):
        """build_system_prompt should surface exceptions raised by CodebaseService.read_file."""

        pass

    def test_build_active_context_xml_returns_empty_when_workspace_returns_none(self):
        """_build_active_context_xml should return empty string when workspace returns no active files."""

        pass

    def test_build_active_context_xml_skips_files_with_non_successful_reads(self):
        """_build_active_context_xml should skip entries where read_file status is not SUCCESS."""

        pass

    def test_build_active_context_xml_handles_duplicate_paths(self):
        """_build_active_context_xml should define behavior for duplicate file paths (include or dedupe)."""

        pass

    def test_build_active_context_xml_includes_file_tag_with_path_attribute(self):
        """_build_active_context_xml should wrap each file in a <FILE path="..."> tag."""

        pass

    def test_build_active_context_xml_preserves_file_content_exactly(self):
        """_build_active_context_xml should embed file content without mutation."""

        pass

    def test_build_prompts_xml_wraps_each_prompt_in_instruction_tag(self):
        """_build_prompts_xml should wrap each prompt in an <INSTRUCTION name="..."> tag."""

        pass

    def test_build_prompts_xml_preserves_prompt_content(self):
        """_build_prompts_xml should embed prompt content without mutation."""

        pass

    def test_build_prompts_xml_returns_empty_when_no_active_prompts(self):
        """_build_prompts_xml should return empty string when there are no active prompts."""

        pass

    def test_build_system_prompt_excludes_active_context_when_all_reads_fail(self):
        """build_system_prompt should omit ACTIVE_CONTEXT when no files are successfully read."""

        pass

    def test_build_system_prompt_excludes_repo_map_when_repo_map_is_none(self):
        """build_system_prompt should omit REPOSITORY_MAP when repo map service returns None."""

        pass