import pytest

from app.projects.exceptions import MultipleActiveProjectsException
from app.projects.models import Project
from app.projects.repositories import ProjectRepository
from app.projects.schemas import ProjectCreate


class TestProjectRepository:
    async def test_list_orders_by_name(
        self,
        project_repository: ProjectRepository,
        project: Project,
    ) -> None:
        await project_repository.create(obj_in=ProjectCreate(name="B Project", path="/tmp/b"))
        await project_repository.create(obj_in=ProjectCreate(name="A Project", path="/tmp/a"))

        result = await project_repository.list()
        names = [p.name for p in result]
        assert "A Project" in names
        assert "B Project" in names

        idx_a = names.index("A Project")
        idx_b = names.index("B Project")
        assert idx_a < idx_b

    @pytest.mark.parametrize("active_count", [0, 1])
    async def test_get_active_returns_none_or_project(
        self,
        active_count: int,
        project_repository: ProjectRepository,
        project: Project,
    ) -> None:
        # Deactivate the default project fixture to start with 0 active
        await project_repository.deactivate(project)

        await project_repository.create(obj_in=ProjectCreate(name="Inactive", path="/tmp/inactive"))
        if active_count == 1:
            # Create exactly ONE active project
            created = await project_repository.create(obj_in=ProjectCreate(name="Active", path="/tmp/active"))
            await project_repository.activate(created)

        active = await project_repository.get_active()
        if active_count == 0:
            assert active is None
        else:
            assert active is not None
            assert active.is_active is True

    async def test_get_active_raises_when_multiple_active(
        self,
        project_repository: ProjectRepository,
        project: Project,
    ) -> None:
        # The 'project' fixture is already active. Create ONE more to force exception.
        active_2 = await project_repository.create(obj_in=ProjectCreate(name="Active 2", path="/tmp/a2"))
        await project_repository.activate(active_2)

        with pytest.raises(MultipleActiveProjectsException):
            await project_repository.get_active()

    async def test_activate_and_deactivate_persist(
        self,
        project_repository: ProjectRepository,
        project_inactive: Project,
        db_session,
    ) -> None:
        assert project_inactive.is_active is False

        activated = await project_repository.activate(project_inactive)
        assert activated.is_active is True
        await db_session.refresh(project_inactive)
        assert project_inactive.is_active is True

        deactivated = await project_repository.deactivate(project_inactive)
        assert deactivated.is_active is False
        await db_session.refresh(project_inactive)
        assert project_inactive.is_active is False
