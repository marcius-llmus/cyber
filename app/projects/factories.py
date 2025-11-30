from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.repositories import ProjectRepository
from app.projects.services import ProjectService


async def build_project_service(db: AsyncSession) -> ProjectService:
    repo = ProjectRepository(db)
    return ProjectService(project_repo=repo)
