import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.exceptions import ProjectNotFoundException
from app.projects.models import Project
from app.projects.services import ProjectService
from app.projects.schemas import ProjectCreate


class TestProjectService:
    async def test_get_project_raises_when_missing(
        self,
        project_service: ProjectService,
    ) -> None:
        with pytest.raises(ProjectNotFoundException):
            await project_service.get_project(project_id=999999)

    async def test_get_project_returns_project(
        self,
        project_service: ProjectService,
        project: Project,
    ) -> None:
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

        projects = await project_service.set_active_project(project_id=project_inactive.id)

        await db_session.refresh(project)
        await db_session.refresh(project_inactive)

        assert project.is_active is False
        assert project_inactive.is_active is True

        assert isinstance(projects, list)
        assert {p.id for p in projects} == {project.id, project_inactive.id}
        assert sum(1 for p in projects if p.is_active) == 1
        assert next(p for p in projects if p.is_active).id == project_inactive.id

    async def test_set_active_project_is_idempotent(
        self,
        project_service: ProjectService,
        project: Project,
        db_session: AsyncSession,
    ) -> None:
        assert project.is_active is True
        projects = await project_service.set_active_project(project_id=project.id)

        await db_session.refresh(project)
        assert project.is_active is True

        assert isinstance(projects, list)
        assert [p.id for p in projects] == [project.id]
        assert sum(1 for p in projects if p.is_active) == 1
        assert projects[0].is_active is True

    async def test_get_active_project_returns_active(
        self,
        project_service: ProjectService,
        project: Project,
    ) -> None:
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

        await project_service.project_repo.create(obj_in=ProjectCreate(name="B Project", path="/tmp/b"))
        await project_service.project_repo.create(obj_in=ProjectCreate(name="A Project", path="/tmp/a"))

        projects = await project_service.get_projects()
        names = [p.name for p in projects]
        assert "A Project" in names
        assert "B Project" in names
        assert names.index("A Project") < names.index("B Project")
        sync_mock.assert_awaited_once()
