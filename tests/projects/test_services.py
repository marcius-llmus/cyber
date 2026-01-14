import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock

from app.projects.exceptions import ProjectNotFoundException
from app.projects.models import Project
from app.projects.services import ProjectService
from app.projects.schemas import ProjectCreate


class TestProjectService:
    async def test_get_project_raises_when_missing(
        self,
        project_service: ProjectService,
    ) -> None:
        project_service.project_repo.get = AsyncMock(return_value=None) # BaseRepository.get
        with pytest.raises(ProjectNotFoundException):
            await project_service.get_project(project_id=999999)

    async def test_get_project_returns_project(
        self,
        project_service: ProjectService,
        project: Project,
    ) -> None:
        project_service.project_repo.get = AsyncMock(return_value=project)
        retrieved = await project_service.get_project(project_id=project.id)
        assert retrieved.id == project.id

    async def test_set_active_project_switches_active_project(
        self,
        project_service: ProjectService,
        project: Project,
        project_inactive: Project,
        db_session: AsyncSession,
    ) -> None:
        assert project.is_active is True
        assert project_inactive.is_active is False
        
        project_service.project_repo.get = AsyncMock(return_value=project_inactive)
        project_service.project_repo.get_active = AsyncMock(return_value=project)
        project_service.project_repo.deactivate = AsyncMock()
        project_service.project_repo.activate = AsyncMock()
        project_service.project_repo.list = AsyncMock(return_value=[project, project_inactive])

        projects = await project_service.set_active_project(project_id=project_inactive.id)

        assert isinstance(projects, list)
        project_service.project_repo.get_active.assert_awaited_once()
        project_service.project_repo.deactivate.assert_awaited_once_with(project)
        project_service.project_repo.activate.assert_awaited_once()

    async def test_set_active_project_is_idempotent(
        self,
        project_service: ProjectService,
        project: Project,
        db_session: AsyncSession,
    ) -> None:
        assert project.is_active is True
        project_service.project_repo.get = AsyncMock(return_value=project)
        project_service.project_repo.get_active = AsyncMock(return_value=project)
        project_service.project_repo.list = AsyncMock(return_value=[project])
        
        projects = await project_service.set_active_project(project_id=project.id)

        assert isinstance(projects, list)
        assert [p.id for p in projects] == [project.id]
        project_service.project_repo.get_active.assert_awaited_once()
        # Should not call activate/deactivate if already active

    async def test_get_active_project_returns_active(
        self,
        project_service: ProjectService,
        project: Project,
    ) -> None:
        project_service.project_repo.get_active = AsyncMock(return_value=project)
        active = await project_service.get_active_project()
        assert active is not None
        assert active.id == project.id

    async def test_get_projects_synchronizes_and_lists(
        self,
        project_service: ProjectService,
        project: Project,
        mocker,
    ) -> None:
        # Avoid filesystem dependencies by mocking the synchronizer methods.
        sync_mock = mocker.patch.object(project_service, "_synchronize_projects", autospec=True)

        p1 = Project(name="A Project", path="/tmp/a")
        p2 = Project(name="B Project", path="/tmp/b")
        project_service.project_repo.list = AsyncMock(return_value=[p1, p2])

        projects = await project_service.get_projects()
        names = [p.name for p in projects]
        assert "A Project" in names
        assert "B Project" in names
        assert names.index("A Project") < names.index("B Project")
        sync_mock.assert_awaited_once()