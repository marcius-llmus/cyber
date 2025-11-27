from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.dependencies import get_db
from app.projects.repositories import ProjectRepository
from app.projects.services import ProjectPageService, ProjectService


async def get_project_repository(db: AsyncSession = Depends(get_db)) -> ProjectRepository:
    return ProjectRepository(db=db)


async def build_project_service(db: AsyncSession) -> ProjectService:
    repo = ProjectRepository(db)
    return ProjectService(project_repo=repo)


async def get_project_service(
    db: AsyncSession = Depends(get_db),
) -> ProjectService:
    return await build_project_service(db)


async def get_project_page_service(
    service: ProjectService = Depends(get_project_service),
) -> ProjectPageService:
    return ProjectPageService(project_service=service)
