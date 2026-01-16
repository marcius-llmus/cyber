"""Factory tests for the projects app."""

import pytest

from app.projects.factories import build_project_service
from app.projects.repositories import ProjectRepository
from app.projects.services import ProjectService


class TestProjectsFactories:
    async def test_build_project_service_returns_service(self, db_session_mock):
        service = await build_project_service(db_session_mock)
        assert isinstance(service, ProjectService)

    async def test_build_project_service_wires_repository_with_db(self, db_session_mock):
        service = await build_project_service(db_session_mock)
        assert isinstance(service.project_repo, ProjectRepository)
        assert service.project_repo.db is db_session_mock

    async def test_build_project_service_propagates_errors_from_repository_constructor(
        self, db_session_mock, mocker
    ):
        repo_cls_mock = mocker.patch(
            "app.projects.factories.ProjectRepository",
            side_effect=ValueError("Boom"),
        )

        with pytest.raises(ValueError, match="Boom"):
            await build_project_service(db_session_mock)

        repo_cls_mock.assert_called_once_with(db_session_mock)