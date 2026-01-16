"""Dependency tests for the agents app."""

from unittest.mock import AsyncMock

import pytest

from app.agents.dependencies import get_workflow_service


class TestAgentsDependencies:
    async def test_get_workflow_service_delegates_to_factory_and_returns_instance(
        self,
        db_session_mock,
        mocker,
        workflow_service_mock,
    ):
        build_workflow_service_mock = mocker.patch(
            "app.agents.dependencies.build_workflow_service",
            new=AsyncMock(return_value=workflow_service_mock),
        )

        service = await get_workflow_service(db=db_session_mock)

        assert service is workflow_service_mock
        build_workflow_service_mock.assert_awaited_once_with(db_session_mock)

    async def test_get_workflow_service_propagates_factory_error(
        self,
        db_session_mock,
        mocker,
    ):
        build_workflow_service_mock = mocker.patch(
            "app.agents.dependencies.build_workflow_service",
            new=AsyncMock(side_effect=ValueError("Boom")),
        )

        with pytest.raises(ValueError, match="Boom"):
            await get_workflow_service(db=db_session_mock)

        build_workflow_service_mock.assert_awaited_once_with(db_session_mock)