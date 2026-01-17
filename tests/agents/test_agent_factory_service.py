"""Unit tests for AgentFactoryService.

These tests validate business/orchestration decisions inside AgentFactoryService.build_agent
without touching the database.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.services.agent_factory import AgentFactoryService
from app.core.enums import OperationalMode
from app.llms.enums import LLMModel
from app.settings.models import Settings
from app.context.tools import FileTools, SearchTools
from app.patches.tools import PatcherTools


class TestAgentFactoryService:
    async def test_build_agent_uses_settings_and_llm_settings_to_create_llm_client(
        self,
        agent_factory_service: AgentFactoryService,
        settings_service_mock,
        llm_service_mock,
        session_service_mock,
        agent_context_service_mock,
        fake_llm_client,
        llm_settings_coder_mock,
        coder_agent_mock,
        mocker,
    ):
        """Should request settings + coding llm settings and build llm client with expected args."""

        settings = Settings(
            max_history_length=50,
            coding_llm_temperature=float(Decimal("0.7")),
            ast_token_limit=2000,
            grep_token_limit=4000,
        )

        settings_service_mock.get_settings = AsyncMock(return_value=settings)
        llm_service_mock.get_coding_llm = AsyncMock(return_value=llm_settings_coder_mock)
        llm_service_mock.get_client = AsyncMock(return_value=fake_llm_client)
        session_service_mock.get_operational_mode = AsyncMock(return_value=OperationalMode.CHAT)
        agent_context_service_mock.build_system_prompt = AsyncMock(return_value="PROMPT")

        coder_agent_cls_mock = mocker.patch(
            "app.agents.services.agent_factory.CoderAgent",
            return_value=coder_agent_mock,
        )

        agent = await agent_factory_service.build_agent(session_id=123)

        assert agent is coder_agent_mock

        settings_service_mock.get_settings.assert_awaited_once_with()
        llm_service_mock.get_coding_llm.assert_awaited_once_with()
        llm_service_mock.get_client.assert_awaited_once_with(
            model_name=LLMModel(llm_settings_coder_mock.model_name),
            temperature=settings.coding_llm_temperature,
        )
        session_service_mock.get_operational_mode.assert_awaited_once_with(123)
        agent_context_service_mock.build_system_prompt.assert_awaited_once_with(
            123,
            operational_mode=OperationalMode.CHAT,
        )
        coder_agent_cls_mock.assert_called_once()

    async def test_build_agent_requests_operational_mode_from_session_service(
        self,
        agent_factory_service: AgentFactoryService,
        settings_service_mock,
        llm_service_mock,
        session_service_mock,
        agent_context_service_mock,
        fake_llm_client,
        llm_settings_coder_mock,
        coder_agent_mock,
        mocker,
    ):
        """Should await SessionService.get_operational_mode(session_id) exactly once."""
        settings_service_mock.get_settings = AsyncMock(
            return_value=Settings(
                max_history_length=50,
                coding_llm_temperature=float(Decimal("0.1")),
                ast_token_limit=2000,
                grep_token_limit=4000,
            )
        )
        llm_service_mock.get_coding_llm = AsyncMock(return_value=llm_settings_coder_mock)
        llm_service_mock.get_client = AsyncMock(return_value=fake_llm_client)

        session_service_mock.get_operational_mode = AsyncMock(return_value=OperationalMode.CHAT)
        agent_context_service_mock.build_system_prompt = AsyncMock(return_value="PROMPT")
        mocker.patch("app.agents.services.agent_factory.CoderAgent", return_value=coder_agent_mock)

        await agent_factory_service.build_agent(session_id=999)

        session_service_mock.get_operational_mode.assert_awaited_once_with(999)

    async def test_build_agent_builds_system_prompt_with_operational_mode(
        self,
        agent_factory_service: AgentFactoryService,
        settings_service_mock,
        llm_service_mock,
        session_service_mock,
        agent_context_service_mock,
        fake_llm_client,
        llm_settings_coder_mock,
        coder_agent_mock,
        mocker,
    ):
        """Should call AgentContextService.build_system_prompt(session_id, operational_mode=mode)."""
        settings_service_mock.get_settings = AsyncMock(
            return_value=Settings(
                max_history_length=50,
                coding_llm_temperature=float(Decimal("0.1")),
                ast_token_limit=2000,
                grep_token_limit=4000,
            )
        )
        llm_service_mock.get_coding_llm = AsyncMock(return_value=llm_settings_coder_mock)
        llm_service_mock.get_client = AsyncMock(return_value=fake_llm_client)

        session_service_mock.get_operational_mode = AsyncMock(return_value=OperationalMode.PLANNER)
        agent_context_service_mock.build_system_prompt = AsyncMock(return_value="PROMPT")
        mocker.patch("app.agents.services.agent_factory.CoderAgent", return_value=coder_agent_mock)

        await agent_factory_service.build_agent(session_id=1)

        agent_context_service_mock.build_system_prompt.assert_awaited_once_with(
            1,
            operational_mode=OperationalMode.PLANNER,
        )

    @pytest.mark.parametrize(
        "mode, expect_search, expect_file, expect_patcher",
        [
            (OperationalMode.CODING, True, True, True),
            (OperationalMode.ASK, True, True, False),
            (OperationalMode.PLANNER, True, True, False),
            (OperationalMode.CHAT, False, False, False),
            (OperationalMode.SINGLE_SHOT, False, False, False),
        ],
    )
    async def test_build_agent_tool_construction_by_operational_mode(
        self,
        mode: OperationalMode,
        expect_search: bool,
        expect_file: bool,
        expect_patcher: bool,
        agent_factory_service: AgentFactoryService,
        search_tools_inst,
        file_tools_inst,
        patcher_tools_inst,
        settings_service_mock,
        llm_service_mock,
        session_service_mock,
        agent_context_service_mock,
        fake_llm_client,
        llm_settings_coder_mock,
        coder_agent_mock,
        mocker,
    ):
        """Should include tools based on operational mode (read-only vs patcher)."""
        settings = Settings(
            max_history_length=50,
            coding_llm_temperature=float(Decimal("0.1")),
            ast_token_limit=2000,
            grep_token_limit=4000,
        )
        settings_service_mock.get_settings = AsyncMock(return_value=settings)
        llm_service_mock.get_coding_llm = AsyncMock(return_value=llm_settings_coder_mock)
        llm_service_mock.get_client = AsyncMock(return_value=fake_llm_client)
        session_service_mock.get_operational_mode = AsyncMock(return_value=mode)
        agent_context_service_mock.build_system_prompt = AsyncMock(return_value="PROMPT")

        search_tools_cls_mock = mocker.patch(
            "app.agents.services.agent_factory.SearchTools",
            return_value=search_tools_inst,
        )
        file_tools_cls_mock = mocker.patch(
            "app.agents.services.agent_factory.FileTools",
            return_value=file_tools_inst,
        )
        patcher_tools_cls_mock = mocker.patch(
            "app.agents.services.agent_factory.PatcherTools",
            return_value=patcher_tools_inst,
        )

        coder_agent_cls_mock = mocker.patch(
            "app.agents.services.agent_factory.CoderAgent",
            return_value=coder_agent_mock,
        )

        await agent_factory_service.build_agent(session_id=1, turn_id="t")

        if expect_search:
            search_tools_cls_mock.assert_called_once()
        else:
            search_tools_cls_mock.assert_not_called()

        if expect_file:
            file_tools_cls_mock.assert_called_once()
        else:
            file_tools_cls_mock.assert_not_called()

        if expect_patcher:
            patcher_tools_cls_mock.assert_called_once()
        else:
            patcher_tools_cls_mock.assert_not_called()

        expected_tools = []
        if expect_search:
            expected_tools.extend(["S"])
        if expect_file:
            expected_tools.extend(["F"])
        if expect_patcher:
            expected_tools.extend(["P"])

        coder_agent_cls_mock.assert_called_once_with(
            tools=expected_tools,
            llm=fake_llm_client,
            system_prompt="PROMPT",
        )

    async def test_build_agent_passes_turn_id_to_file_and_patcher_tools(
        self,
        agent_factory_service: AgentFactoryService,
        search_tools_inst,
        file_tools_inst,
        patcher_tools_inst,
        settings_service_mock,
        llm_service_mock,
        session_service_mock,
        agent_context_service_mock,
        fake_llm_client,
        llm_settings_coder_mock,
        coder_agent_mock,
        mocker,
    ):
        """Should pass turn_id into FileTools/PatcherTools constructors."""
        settings = Settings(
            max_history_length=50,
            coding_llm_temperature=float(Decimal("0.1")),
            ast_token_limit=2000,
            grep_token_limit=4000,
        )
        settings_service_mock.get_settings = AsyncMock(return_value=settings)
        llm_service_mock.get_coding_llm = AsyncMock(return_value=llm_settings_coder_mock)
        llm_service_mock.get_client = AsyncMock(return_value=fake_llm_client)
        session_service_mock.get_operational_mode = AsyncMock(return_value=OperationalMode.CODING)
        agent_context_service_mock.build_system_prompt = AsyncMock(return_value="PROMPT")

        mocker.patch("app.agents.services.agent_factory.SearchTools", return_value=search_tools_inst)
        file_tools_cls_mock = mocker.patch(
            "app.agents.services.agent_factory.FileTools",
            return_value=file_tools_inst,
        )
        patcher_tools_cls_mock = mocker.patch(
            "app.agents.services.agent_factory.PatcherTools",
            return_value=patcher_tools_inst,
        )
        mocker.patch("app.agents.services.agent_factory.CoderAgent", return_value=coder_agent_mock)

        await agent_factory_service.build_agent(session_id=1, turn_id="turn_123")

        # kwargs are easiest to assert; we don't care about db/sessionmanager identity here.
        assert file_tools_cls_mock.call_args.kwargs["turn_id"] == "turn_123"
        assert patcher_tools_cls_mock.call_args.kwargs["turn_id"] == "turn_123"

    async def test_build_agent_propagates_error_from_settings_service(
        self,
        agent_factory_service: AgentFactoryService,
        settings_service_mock,
    ):
        """Should surface exceptions from SettingsService.get_settings."""
        settings_service_mock.get_settings = AsyncMock(side_effect=ValueError("Boom"))

        with pytest.raises(ValueError, match="Boom"):
            await agent_factory_service.build_agent(session_id=1)

        settings_service_mock.get_settings.assert_awaited_once_with()

    async def test_build_agent_propagates_error_from_llm_service_get_client(
        self,
        agent_factory_service: AgentFactoryService,
        settings_service_mock,
        llm_service_mock,
        llm_settings_coder_mock,
    ):
        """Should surface exceptions from LLMService.get_client."""
        settings_service_mock.get_settings = AsyncMock(
            return_value=Settings(
                max_history_length=50,
                coding_llm_temperature=float(Decimal("0.1")),
                ast_token_limit=2000,
                grep_token_limit=4000,
            )
        )
        llm_service_mock.get_coding_llm = AsyncMock(return_value=llm_settings_coder_mock)
        llm_service_mock.get_client = AsyncMock(side_effect=ValueError("Boom"))

        with pytest.raises(ValueError, match="Boom"):
            await agent_factory_service.build_agent(session_id=1)

        llm_service_mock.get_client.assert_awaited_once()

    async def test_build_agent_propagates_error_from_agent_context_service(
        self,
        agent_factory_service: AgentFactoryService,
        settings_service_mock,
        llm_service_mock,
        session_service_mock,
        agent_context_service_mock,
        fake_llm_client,
        llm_settings_coder_mock,
    ):
        """Should surface exceptions from AgentContextService.build_system_prompt."""
        settings_service_mock.get_settings = AsyncMock(
            return_value=Settings(
                max_history_length=50,
                coding_llm_temperature=float(Decimal("0.1")),
                ast_token_limit=2000,
                grep_token_limit=4000,
            )
        )
        llm_service_mock.get_coding_llm = AsyncMock(return_value=llm_settings_coder_mock)
        llm_service_mock.get_client = AsyncMock(return_value=fake_llm_client)
        session_service_mock.get_operational_mode = AsyncMock(return_value=OperationalMode.CHAT)
        agent_context_service_mock.build_system_prompt = AsyncMock(side_effect=ValueError("Boom"))

        with pytest.raises(ValueError, match="Boom"):
            await agent_factory_service.build_agent(session_id=1)

        agent_context_service_mock.build_system_prompt.assert_awaited_once()