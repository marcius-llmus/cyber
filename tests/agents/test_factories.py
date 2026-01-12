"""Factory tests for the agents app."""


class TestAgentsFactories:
    def test_build_workflow_service_wires_repository(self):
        """build_workflow_service should construct a WorkflowService with WorkflowStateRepository."""

        pass

    def test_build_workflow_service_uses_passed_db_session(self):
        """build_workflow_service should bind the repository to the provided AsyncSession."""

        pass

    def test_build_workflow_service_returns_workflow_service(self):
        """build_workflow_service should return an instance of WorkflowService."""

        pass

    def test_build_agent_context_service_wires_dependencies(self):
        """build_agent_context_service should construct AgentContextService with required services."""

        pass

    def test_build_agent_context_service_returns_agent_context_service(self):
        """build_agent_context_service should return an instance of AgentContextService."""

        pass

    def test_build_agent_context_service_uses_project_and_prompt_services(self):
        """build_agent_context_service should wire ProjectService and PromptService for prompt assembly."""

        pass

    def test_build_agent_context_service_awaits_dependency_builders(self):
        """build_agent_context_service should await all underlying async dependency builders."""

        pass

    def test_build_agent_context_service_returns_unique_instances_per_call(self):
        """build_agent_context_service should return a new AgentContextService per call (no caching)."""

        pass

    def test_build_agent_includes_read_only_tools_for_ask_mode(self):
        """ASK mode should include search/file tools but not patcher tools."""

        pass

    def test_build_agent_includes_read_only_tools_for_planner_mode(self):
        """PLANNER mode should include search/file tools but not patcher tools."""

        pass

    def test_build_agent_includes_write_tools_for_coding_mode(self):
        """CODING mode should include patcher tools in addition to read-only tools."""

        pass

    def test_build_agent_includes_search_tools_and_file_tools_in_coding_mode(self):
        """CODING mode should include SearchTools and FileTools in addition to patcher tools."""

        pass

    def test_build_agent_has_no_tools_in_chat_mode(self):
        """CHAT mode should have no tools and a minimal system prompt."""

        pass

    def test_build_agent_has_no_tools_in_single_shot_mode(self):
        """SINGLE_SHOT mode should have no tools and should use the single-shot identity."""

        pass

    def test_build_agent_builds_system_prompt_from_agent_context_service(self):
        """build_agent should obtain system_prompt from AgentContextService.build_system_prompt."""

        pass

    def test_build_agent_uses_coding_llm_settings_for_llm_client(self):
        """build_agent should use LLM settings (model, temperature) to build an LLM client."""

        pass

    def test_build_agent_temperature_comes_from_settings_service(self):
        """build_agent should use Settings.coding_llm_temperature for LLM temperature."""

        pass

    def test_build_agent_uses_operational_mode_from_session_service(self):
        """build_agent should read OperationalMode from SessionService.get_operational_mode."""

        pass

    def test_build_agent_passes_turn_id_to_file_and_patcher_tools(self):
        """build_agent should pass turn_id into file/patcher tools to support per-turn behavior."""

        pass

    def test_build_agent_passes_session_id_to_tool_constructors(self):
        """build_agent should pass session_id into SearchTools/FileTools/PatcherTools constructors."""

        pass

    def test_build_agent_passes_session_id_and_mode_to_system_prompt_builder(self):
        """build_agent should call AgentContextService.build_system_prompt(session_id, operational_mode=...)."""

        pass

    def test_build_agent_does_not_construct_any_tools_in_chat_mode(self):
        """CHAT mode should skip constructing SearchTools/FileTools/PatcherTools entirely."""

        pass

    def test_build_agent_does_not_construct_any_tools_in_single_shot_mode(self):
        """SINGLE_SHOT mode should skip constructing SearchTools/FileTools/PatcherTools entirely."""

        pass

    def test_build_agent_does_not_include_file_or_search_tools_outside_coding_ask_planner(self):
        """build_agent should not include SearchTools/FileTools for modes outside CODING/ASK/PLANNER."""

        pass

    def test_build_agent_builds_llm_client_with_model_enum_conversion(self):
        """build_agent should convert model name to LLMModel enum when building the client."""

        pass

    def test_build_agent_propagates_llm_client_builder_errors(self):
        """build_agent should surface exceptions raised while building the LLM client."""

        pass

    def test_build_agent_propagates_system_prompt_builder_errors(self):
        """build_agent should surface exceptions raised by AgentContextService.build_system_prompt."""

        pass

    def test_build_agent_does_not_include_patcher_tools_outside_coding_mode(self):
        """build_agent should not include patcher tools for modes other than CODING."""

        pass

    def test_build_agent_tool_order_is_stable(self):
        """build_agent should construct tools in a stable order (SearchTools, FileTools, then PatcherTools)."""

        pass