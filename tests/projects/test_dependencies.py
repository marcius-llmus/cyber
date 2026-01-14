"""Dependency tests for the projects app."""

import inspect
from unittest.mock import patch

import pytest

from app.projects.dependencies import (
    get_project_page_service,
    get_project_repository,
    get_project_service,
)
from app.projects.repositories import ProjectRepository
from app.projects.services import ProjectPageService, ProjectService


@pytest.mark.asyncio
class TestProjectsDependencies:
    async def test_get_project_repository_returns_repository(self, db_session):
        repo = await get_project_repository(db=db_session)
        assert isinstance(repo, ProjectRepository)
        assert repo.db is db_session

    async def test_get_project_service_is_async_dependency(self):
        assert inspect.iscoroutinefunction(get_project_service)

    async def test_get_project_service_returns_service_instance(self, db_session):
        service = await get_project_service(db=db_session)
        assert isinstance(service, ProjectService)
        assert service.project_repo.db is db_session

    async def test_get_project_page_service_wires_project_service(self, db_session):
        service = await get_project_service(db=db_session)
        page_service = await get_project_page_service(service=service)
        assert isinstance(page_service, ProjectPageService)
        assert page_service.project_service is service

    async def test_get_project_service_propagates_factory_errors(self, db_session):
        with patch(
            "app.projects.dependencies.build_project_service",
            side_effect=Exception("Factory Error"),
        ):
            with pytest.raises(Exception, match="Factory Error"):
                await get_project_service(db=db_session)
