"""Model tests for the projects app."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.models import Project


class TestProjectModel:
    @pytest.mark.asyncio
    async def test_project_can_be_persisted(self, db_session: AsyncSession):
        project = Project(name="My Project", path="/tmp/my_project", is_active=False)
        db_session.add(project)
        await db_session.flush()

        retrieved = await db_session.get(Project, project.id)
        assert retrieved is not None
        assert retrieved.name == "My Project"
        assert retrieved.path == "/tmp/my_project"
        assert retrieved.is_active is False

    @pytest.mark.asyncio
    async def test_project_name_must_be_unique(self, db_session: AsyncSession):
        db_session.add(Project(name="Dup", path="/tmp/dup1", is_active=False))
        db_session.add(Project(name="Dup", path="/tmp/dup2", is_active=False))
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_project_path_must_be_unique(self, db_session: AsyncSession):
        db_session.add(Project(name="P1", path="/tmp/dup_path", is_active=False))
        db_session.add(Project(name="P2", path="/tmp/dup_path", is_active=False))
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_project_is_active_defaults_to_false(self, db_session: AsyncSession):
        project = Project(name="Defaults", path="/tmp/defaults")
        db_session.add(project)
        await db_session.flush()

        stmt = select(Project).where(Project.id == project.id)
        result = await db_session.execute(stmt)
        retrieved = result.scalar_one()

        assert retrieved.is_active in (False, 0)
