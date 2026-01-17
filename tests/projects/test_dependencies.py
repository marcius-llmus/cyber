"""Dependency tests for the projects app."""

import inspect
from unittest.mock import AsyncMock

import pytest

from app.projects.dependencies import (
    get_project_page_service,
    get_project_repository,
    get_project_service,
)
from app.projects.repositories import ProjectRepository
from app.projects.services import ProjectPageService


class TestProjectsDependencies:
    async def test_get_project_repository_returns_repository(self, db_session_mock):
        repo = await get_project_repository(db=db_session_mock)
        assert isinstance(repo, ProjectRepository)
        assert repo.db is db_session_mock

    async def test_get_project_service_is_async_dependency(self):
        assert inspect.iscoroutinefunction(get_project_service)

    async def test_get_project_service_returns_service_instance(
        self, db_session_mock, mocker, project_service_mock
    ):
        build_project_service_mock = mocker.patch(
            "app.projects.dependencies.build_project_service",
            new=AsyncMock(return_value=project_service_mock),
        )

        service = await get_project_service(db=db_session_mock)

        assert service is project_service_mock
        build_project_service_mock.assert_awaited_once_with(db_session_mock)

    async def test_get_project_page_service_wires_project_service(self, project_service_mock):
        service = project_service_mock
        page_service = await get_project_page_service(service=service)

        assert isinstance(page_service, ProjectPageService)
        assert page_service.project_service is service

    async def test_get_project_service_propagates_factory_errors(self, db_session_mock, mocker):
        build_project_service_mock = mocker.patch(
            "app.projects.dependencies.build_project_service",
            new=AsyncMock(side_effect=ValueError("Boom")),
        )

        with pytest.raises(ValueError, match="Boom"):
            await get_project_service(db=db_session_mock)

        build_project_service_mock.assert_awaited_once_with(db_session_mock)
