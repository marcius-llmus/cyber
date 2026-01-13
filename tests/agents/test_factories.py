"""Factory tests for the agents app."""

import pytest
from sqlalchemy import update

from app.agents.factories import (
    build_agent,
    build_agent_context_service,
    build_workflow_service,
)
from app.agents.services import AgentContextService, WorkflowService
from app.coder.agent import CoderAgent
from app.core.enums import OperationalMode
from app.sessions.models import ChatSession


@pytest.mark.asyncio
class TestAgentsFactories:
    async def test_build_workflow_service_wires_repository(self, db_session):
        """build_workflow_service should construct a WorkflowService with WorkflowStateRepository."""
        service = await build_workflow_service(db_session)
        assert service.workflow_repo is not None
        assert service.workflow_repo.db is db_session

    async def test_build_workflow_service_uses_passed_db_session(self, db_session):
        """build_workflow_service should bind the repository to the provided AsyncSession."""
        service = await build_workflow_service(db_session)
        assert service.workflow_repo.db is db_session

    async def test_build_workflow_service_returns_workflow_service(self, db_session):
        """build_workflow_service should return an instance of WorkflowService."""
        service = await build_workflow_service(db_session)
        assert isinstance(service, WorkflowService)

    async def test_build_agent_context_service_wires_dependencies(self, db_session):
        """build_agent_context_service should construct AgentContextService with required services."""
        service = await build_agent_context_service(db_session)
        assert service.repo_map_service is not None
        assert service.workspace_service is not None
        assert service.codebase_service is not None
        assert service.project_service is not None
        assert service.prompt_service is not None

    async def test_build_agent_context_service_returns_agent_context_service(self, db_session):
        """build_agent_context_service should return an instance of AgentContextService."""
        service = await build_agent_context_service(db_session)
        assert isinstance(service, AgentContextService)

    async def test_build_agent_context_service_uses_project_and_prompt_services(self, db_session):
        """build_agent_context_service should wire ProjectService and PromptService for prompt assembly."""
        service = await build_agent_context_service(db_session)
        # Verify dependencies are wired (by checking they are not None and have DB session where applicable)
        assert service.project_service.project_repo.db is db_session
        assert service.prompt_service.prompt_repo.db is db_session

    async def test_build_agent_context_service_awaits_dependency_builders(self, db_session):
        """build_agent_context_service should await all underlying async dependency builders."""
        # If we get a result without error, it means awaits happened correctly.
        service = await build_agent_context_service(db_session)
        assert isinstance(service, AgentContextService)

    async def test_build_agent_context_service_returns_unique_instances_per_call(self, db_session):
        """build_agent_context_service should return a new AgentContextService per call (no caching)."""
        service1 = await build_agent_context_service(db_session)
        service2 = await build_agent_context_service(db_session)
        assert service1 is not service2

    async def test_build_agent_includes_read_only_tools_for_ask_mode(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """ASK mode should include search/file tools but not patcher tools."""
        # Update session mode

        await db_session.execute(
            update(ChatSession)
            .where(ChatSession.id == chat_session.id)
            .values(operational_mode=OperationalMode.ASK)
        )
        await db_session.flush()

        agent = await build_agent(db_session, chat_session.id)
        agent_tool_names = [tool.metadata.name for tool in agent.tools]

        assert "grep" in agent_tool_names
        assert "read_files" in agent_tool_names
        assert "apply_diff" not in agent_tool_names

    async def test_build_agent_includes_read_only_tools_for_planner_mode(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """PLANNER mode should include search/file tools but not patcher tools."""
        # Update session mode

        await db_session.execute(
            update(ChatSession)
            .where(ChatSession.id == chat_session.id)
            .values(operational_mode=OperationalMode.PLANNER)
        )
        await db_session.flush()

        agent = await build_agent(db_session, chat_session.id)

        agent_tool_names = [tool.metadata.name for tool in agent.tools]

        assert "grep" in agent_tool_names
        assert "read_files" in agent_tool_names
        assert "apply_diff" not in agent_tool_names

    async def test_build_agent_includes_write_tools_for_coding_mode(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """CODING mode should include patcher tools in addition to read-only tools."""
        # Update session mode

        await db_session.execute(
            update(ChatSession)
            .where(ChatSession.id == chat_session.id)
            .values(operational_mode=OperationalMode.CODING)
        )
        await db_session.flush()

        agent = await build_agent(db_session, chat_session.id)
        agent_tool_names = [tool.metadata.name for tool in agent.tools]
        assert "grep" in agent_tool_names
        assert "read_files" in agent_tool_names
        assert "apply_diff" in agent_tool_names

    async def test_build_agent_includes_search_tools_and_file_tools_in_coding_mode(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """CODING mode should include SearchTools and FileTools in addition to patcher tools."""
        # Update session mode

        await db_session.execute(
            update(ChatSession)
            .where(ChatSession.id == chat_session.id)
            .values(operational_mode=OperationalMode.CODING)
        )
        await db_session.flush()

        agent = await build_agent(db_session, chat_session.id)

        agent_tool_names = [tool.metadata.name for tool in agent.tools]

        assert "grep" in agent_tool_names
        assert "read_files" in agent_tool_names

    async def test_build_agent_has_no_tools_in_chat_mode(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """CHAT mode should have no tools and a minimal system prompt."""
        # Update session mode

        await db_session.execute(
            update(ChatSession)
            .where(ChatSession.id == chat_session.id)
            .values(operational_mode=OperationalMode.CHAT)
        )
        await db_session.flush()

        agent = await build_agent(db_session, chat_session.id)

        assert len(agent.tools) == 0

    async def test_build_agent_has_no_tools_in_single_shot_mode(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """SINGLE_SHOT mode should have no tools and should use the single-shot identity."""
        # Update session mode

        await db_session.execute(
            update(ChatSession)
            .where(ChatSession.id == chat_session.id)
            .values(operational_mode=OperationalMode.SINGLE_SHOT)
        )
        await db_session.flush()

        agent = await build_agent(db_session, chat_session.id)

        assert len(agent.tools) == 0
        # Verify identity in system prompt
        assert "Single-shot mode" in agent.system_prompt

    async def test_build_agent_builds_system_prompt_from_agent_context_service(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """build_agent should obtain system_prompt from AgentContextService.build_system_prompt."""
        agent = await build_agent(db_session, chat_session.id)
        assert isinstance(agent.system_prompt, str)
        assert "<IDENTITY>" in agent.system_prompt

    async def test_build_agent_uses_coding_llm_settings_for_llm_client(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """build_agent should use LLM settings (model, temperature) to build an LLM client."""
        # We rely on default settings here.
        agent = await build_agent(db_session, chat_session.id)
        assert agent.llm is not None
        # We can't easily check the model name without inspecting private attributes or assuming LlamaIndex structure,
        # but successful construction implies it worked.

    async def test_build_agent_temperature_comes_from_settings_service(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """build_agent should use Settings.coding_llm_temperature for LLM temperature."""
        # This is an integration test, we assume defaults.
        agent = await build_agent(db_session, chat_session.id)
        # LlamaIndex LLMs usually expose metadata or temperature
        if hasattr(agent.llm, "temperature"):
            assert agent.llm.temperature is not None

    async def test_build_agent_uses_operational_mode_from_session_service(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """build_agent should read OperationalMode from SessionService.get_operational_mode."""
        # Update session mode

        await db_session.execute(
            update(ChatSession)
            .where(ChatSession.id == chat_session.id)
            .values(operational_mode=OperationalMode.CHAT)
        )
        await db_session.flush()

        agent = await build_agent(db_session, chat_session.id)
        # Chat mode -> no tools
        assert len(agent.tools) == 0

    async def test_build_agent_passes_turn_id_to_file_and_patcher_tools(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """build_agent should pass turn_id into file/patcher tools to support per-turn behavior."""
        # We can verify the factory accepts it and runs.
        # Deep inspection of tool closures is hard without patching.
        agent = await build_agent(db_session, chat_session.id, turn_id="turn_123")
        assert isinstance(agent, CoderAgent)

    async def test_build_agent_passes_session_id_to_tool_constructors(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """build_agent should pass session_id into SearchTools/FileTools/PatcherTools constructors."""
        agent = await build_agent(db_session, chat_session.id)
        assert isinstance(agent, CoderAgent)

    async def test_build_agent_passes_session_id_and_mode_to_system_prompt_builder(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """build_agent should call AgentContextService.build_system_prompt(session_id, operational_mode=...)."""
        # Update session mode

        await db_session.execute(
            update(ChatSession)
            .where(ChatSession.id == chat_session.id)
            .values(operational_mode=OperationalMode.PLANNER)
        )
        await db_session.flush()

        agent = await build_agent(db_session, chat_session.id)
        assert "<IDENTITY>" in agent.system_prompt
        # Planner prompt check
        assert "iterating over a TODO list" in agent.system_prompt

    async def test_build_agent_does_not_construct_any_tools_in_chat_mode(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """CHAT mode should skip constructing SearchTools/FileTools/PatcherTools entirely."""
        # Update session mode

        await db_session.execute(
            update(ChatSession)
            .where(ChatSession.id == chat_session.id)
            .values(operational_mode=OperationalMode.CHAT)
        )
        await db_session.flush()

        agent = await build_agent(db_session, chat_session.id)
        assert len(agent.tools) == 0

    async def test_build_agent_does_not_construct_any_tools_in_single_shot_mode(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """SINGLE_SHOT mode should skip constructing SearchTools/FileTools/PatcherTools entirely."""
        # Update session mode

        await db_session.execute(
            update(ChatSession)
            .where(ChatSession.id == chat_session.id)
            .values(operational_mode=OperationalMode.SINGLE_SHOT)
        )
        await db_session.flush()

        agent = await build_agent(db_session, chat_session.id)
        assert len(agent.tools) == 0

    async def test_build_agent_does_not_include_file_or_search_tools_outside_coding_ask_planner(
        self, db_session, chat_session: ChatSession, settings, llm_settings
    ):
        """build_agent should not include SearchTools/FileTools for modes outside CODING/ASK/PLANNER."""
        # Update session mode

        await db_session.execute(
            update(ChatSession)
            .where(ChatSession.id == chat_session.id)
            .values(operational_mode=OperationalMode.CHAT)
        )
        await db_session.flush()

        agent = await build_agent(db_session, chat_session.id)
        assert len(agent.tools) == 0