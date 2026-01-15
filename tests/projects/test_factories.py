"""Factory tests for the projects app."""

import pytest

from app.projects.factories import build_project_service
from app.projects.services import ProjectService


class TestProjectsFactories:
    async def test_build_project_service_returns_service(self, db_session_mock):
        service = await build_project_service(db_session_mock)
        assert isinstance(service, ProjectService)

    async def test_build_project_service_wires_repository_with_db(self, db_session_mock):
        service = await build_project_service(db_session_mock)
        assert service.project_repo is not None
        assert service.project_repo.db is db_session_mock