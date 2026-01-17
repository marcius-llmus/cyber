from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.dependencies import get_db
from app.context.factories import build_filesystem_service, build_workspace_service
from app.context.repositories import ContextRepository
from app.context.services import ContextPageService, FileSystemService, WorkspaceService
from app.projects.dependencies import get_project_service
from app.projects.services import ProjectService


async def get_context_repository(db: AsyncSession = Depends(get_db)) -> ContextRepository:
    return ContextRepository(db)


async def get_filesystem_service(
    db: AsyncSession = Depends(get_db),
) -> FileSystemService:
    return await build_filesystem_service(db)


async def get_context_service(
    db: AsyncSession = Depends(get_db),
) -> WorkspaceService:
    return await build_workspace_service(db)


async def get_context_page_service(
    context_service: WorkspaceService = Depends(get_context_service),
    fs_service: FileSystemService = Depends(get_filesystem_service),
    project_service: ProjectService = Depends(get_project_service),
) -> ContextPageService:
    return ContextPageService(
        context_service=context_service,
        fs_service=fs_service,
        project_service=project_service,
    )
