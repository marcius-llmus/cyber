"""Dependency tests for the agents app."""

from unittest.mock import patch
import inspect
import pytest
from app.agents.dependencies import get_workflow_service
from app.agents.services import WorkflowService


class TestAgentsDependencies:
    async def test_get_workflow_service_returns_service_instance(self, db_session):
        """get_workflow_service should return a WorkflowService instance."""
        service = await get_workflow_service(db=db_session)
        assert isinstance(service, WorkflowService)

    async def test_get_workflow_service_uses_db_dependency(self, db_session):
        """get_workflow_service should accept a db dependency and pass it to the factory."""
        service = await get_workflow_service(db=db_session)
        assert service.workflow_repo.db == db_session

    async def test_get_workflow_service_is_awaitable(self):
        """get_workflow_service should be an async dependency and await internal wiring."""
        assert inspect.iscoroutinefunction(get_workflow_service)

    async def test_get_workflow_service_is_declared_async(self):
        """get_workflow_service should remain an async dependency (not sync)."""
        assert inspect.iscoroutinefunction(get_workflow_service)

    async def test_get_workflow_service_returns_awaited_factory_result(self, db_session):
        """get_workflow_service should return the awaited result of the underlying factory."""
        service = await get_workflow_service(db=db_session)
        assert isinstance(service, WorkflowService)

    async def test_get_workflow_service_returns_distinct_instances(self, db_session):
        """get_workflow_service should return a new service instance per request by default."""
        service1 = await get_workflow_service(db=db_session)
        service2 = await get_workflow_service(db=db_session)
        assert service1 is not service2

    async def test_get_workflow_service_returns_service_with_repository(self, db_session):
        """WorkflowService returned by get_workflow_service should be wired with a repository."""
        service = await get_workflow_service(db=db_session)
        assert service.workflow_repo is not None

    async def test_get_workflow_service_propagates_factory_errors(self, db_session):
        """get_workflow_service should surface exceptions raised by the underlying factory."""
        with patch("app.agents.dependencies.build_workflow_service", side_effect=Exception("Factory Error")):
            with pytest.raises(Exception, match="Factory Error"):
                await get_workflow_service(db=db_session)