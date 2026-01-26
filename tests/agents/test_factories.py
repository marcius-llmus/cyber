"""Factory tests for the agents app."""

from unittest.mock import AsyncMock

import pytest

from app.agents.factories import (
    build_agent,
    build_agent_context_service,
    build_agent_factory_service,
    build_workflow_service,
)
from app.agents.repositories import WorkflowStateRepository
from app.agents.services import (
    AgentContextService,
    AgentFactoryService,
    WorkflowService,
)


class TestAgentsFactories:
    async def test_build_workflow_service_wires_repository(self, db_session_mock):
        """Factory should wire WorkflowStateRepository(db=db_session_mock) into WorkflowService."""
        service = await build_workflow_service(db_session_mock)

        assert isinstance(service, WorkflowService)
        assert isinstance(service.workflow_repo, WorkflowStateRepository)
        assert service.workflow_repo.db is db_session_mock

    async def test_build_agent_context_service_wires_dependencies_from_subfactories(
        self,
        db_session_mock,
        mocker,
        repo_map_service_mock,
        workspace_service_mock,
        codebase_service_mock,
        project_service_mock,
        prompt_service_mock,
    ):
        """Factory should await subfactories and inject their returned services into AgentContextService."""
        build_repo_map_service_mock = mocker.patch(
            "app.agents.factories.build_repo_map_service",
            new=AsyncMock(return_value=repo_map_service_mock),
        )
        build_workspace_service_mock = mocker.patch(
            "app.agents.factories.build_workspace_service",
            new=AsyncMock(return_value=workspace_service_mock),
        )
        build_codebase_service_mock = mocker.patch(
            "app.agents.factories.build_codebase_service",
            new=AsyncMock(return_value=codebase_service_mock),
        )
        build_project_service_mock = mocker.patch(
            "app.agents.factories.build_project_service",
            new=AsyncMock(return_value=project_service_mock),
        )
        build_prompt_service_mock = mocker.patch(
            "app.agents.factories.build_prompt_service",
            new=AsyncMock(return_value=prompt_service_mock),
        )

        service = await build_agent_context_service(db_session_mock)

        assert isinstance(service, AgentContextService)
        assert service.repo_map_service is repo_map_service_mock
        assert service.workspace_service is workspace_service_mock
        assert service.codebase_service is codebase_service_mock
        assert service.project_service is project_service_mock
        assert service.prompt_service is prompt_service_mock

        build_repo_map_service_mock.assert_awaited_once_with(db_session_mock)
        build_workspace_service_mock.assert_awaited_once_with(db_session_mock)
        # build_codebase_service is called without db
        build_codebase_service_mock.assert_awaited_once_with()
        build_project_service_mock.assert_awaited_once_with(db_session_mock)
        build_prompt_service_mock.assert_awaited_once_with(db_session_mock)

    @pytest.mark.parametrize(
        "patch_target",
        [
            "app.agents.factories.build_repo_map_service",
            "app.agents.factories.build_workspace_service",
            "app.agents.factories.build_project_service",
            "app.agents.factories.build_prompt_service",
        ],
    )
    async def test_build_agent_context_service_propagates_error_from_subfactory(
        self,
        patch_target,
        db_session_mock,
        mocker,
    ):
        """Factory should propagate errors raised by any awaited subfactory."""

        subfactory_mock = mocker.patch(
            patch_target,
            new=AsyncMock(side_effect=ValueError("Boom")),
        )

        with pytest.raises(ValueError, match="Boom"):
            await build_agent_context_service(db_session_mock)

        subfactory_mock.assert_awaited_once_with(db_session_mock)

    async def test_build_agent_context_service_propagates_error_from_codebase_subfactory(
        self,
        db_session_mock,
        mocker,
    ):
        """Factory should propagate errors raised by build_codebase_service() (called without db)."""

        subfactory_mock = mocker.patch(
            "app.agents.factories.build_codebase_service",
            new=AsyncMock(side_effect=ValueError("Boom")),
        )

        with pytest.raises(ValueError, match="Boom"):
            await build_agent_context_service(db_session_mock)

        subfactory_mock.assert_awaited_once_with()

    async def test_build_agent_factory_service_wires_services_from_subfactories(
        self,
        db_session_mock,
        mocker,
        llm_service_mock,
        session_service_mock,
        agent_context_service_mock,
    ):
        """Factory should await and inject llm/session/context services into AgentFactoryService."""

        build_llm_service_mock = mocker.patch(
            "app.agents.factories.build_llm_service",
            new=AsyncMock(return_value=llm_service_mock),
        )
        build_session_service_mock = mocker.patch(
            "app.agents.factories.build_session_service",
            new=AsyncMock(return_value=session_service_mock),
        )
        build_agent_context_service_mock = mocker.patch(
            "app.agents.factories.build_agent_context_service",
            new=AsyncMock(return_value=agent_context_service_mock),
        )

        service = await build_agent_factory_service(db_session_mock)

        assert isinstance(service, AgentFactoryService)
        assert service.llm_service is llm_service_mock
        assert service.session_service is session_service_mock
        assert service.agent_context_service is agent_context_service_mock

        build_llm_service_mock.assert_awaited_once_with(db_session_mock)
        build_session_service_mock.assert_awaited_once_with(db_session_mock)
        build_agent_context_service_mock.assert_awaited_once_with(db_session_mock)

    @pytest.mark.parametrize(
        "patch_target",
        [
            "app.agents.factories.build_llm_service",
            "app.agents.factories.build_session_service",
            "app.agents.factories.build_agent_context_service",
        ],
    )
    async def test_build_agent_factory_service_propagates_error_from_subfactory(
        self,
        patch_target,
        db_session_mock,
        mocker,
    ):
        """Factory should propagate errors raised by any awaited subfactory."""

        subfactory_mock = mocker.patch(
            patch_target,
            new=AsyncMock(side_effect=ValueError("Boom")),
        )

        with pytest.raises(ValueError, match="Boom"):
            await build_agent_factory_service(db_session_mock)

        subfactory_mock.assert_awaited_once_with(db_session_mock)

    async def test_build_agent_delegates_to_agent_factory_service_build_agent(
        self,
        db_session_mock,
        mocker,
        agent_factory_service_mock,
        coder_agent_mock,
        settings_snapshot,
    ):
        """Thin build_agent factory should delegate to AgentFactoryService.build_agent and return it."""
        agent_factory_service_mock.build_agent = AsyncMock(
            return_value=coder_agent_mock
        )

        build_agent_factory_service_mock = mocker.patch(
            "app.agents.factories.build_agent_factory_service",
            new=AsyncMock(return_value=agent_factory_service_mock),
        )

        agent = await build_agent(
            db=db_session_mock,
            session_id=123,
            turn_id="t1",
            settings_snapshot=settings_snapshot,
        )

        assert agent is coder_agent_mock
        build_agent_factory_service_mock.assert_awaited_once_with(db_session_mock)
        agent_factory_service_mock.build_agent.assert_awaited_once_with(
            session_id=123,
            turn_id="t1",
            settings_snapshot=settings_snapshot,
        )

    async def test_build_agent_propagates_error_from_agent_factory_service(
        self,
        db_session_mock,
        mocker,
        agent_factory_service_mock,
        settings_snapshot,
    ):
        """Thin build_agent factory should surface exceptions raised by AgentFactoryService.build_agent."""
        agent_factory_service_mock.build_agent = AsyncMock(
            side_effect=ValueError("Boom")
        )
        build_agent_factory_service_mock = mocker.patch(
            "app.agents.factories.build_agent_factory_service",
            new=AsyncMock(return_value=agent_factory_service_mock),
        )

        with pytest.raises(ValueError, match="Boom"):
            await build_agent(
                db=db_session_mock,
                session_id=123,
                turn_id=None,
                settings_snapshot=settings_snapshot,
            )

        build_agent_factory_service_mock.assert_awaited_once_with(db_session_mock)
        agent_factory_service_mock.build_agent.assert_awaited_once_with(
            session_id=123,
            turn_id=None,
            settings_snapshot=settings_snapshot,
        )
