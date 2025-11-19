from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.repositories import BaseRepository
from app.projects.exceptions import MultipleActiveProjectsException
from app.projects.models import Project


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def list(self) -> list[Project]:
        result = await self.db.execute(select(self.model).order_by(self.model.name))
        return list(result.scalars().all())

    async def get_active(self) -> Project | None:
        result = await self.db.execute(select(self.model).where(self.model.is_active))
        active_projects = list(result.scalars().all())
        if len(active_projects) > 1:
            raise MultipleActiveProjectsException("Multiple active projects found.")
        return active_projects[0] if active_projects else None

    async def activate(self, project: Project) -> Project:
        project.is_active = True
        self.db.add(project)
        await self.db.flush()
        await self.db.refresh(project)
        return project

    async def deactivate(self, project: Project) -> Project:
        project.is_active = False
        self.db.add(project)
        await self.db.flush()
        await self.db.refresh(project)
        return project