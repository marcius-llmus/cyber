from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.dependencies import get_db
from app.projects.dependencies import build_project_service
from app.context.services import CodebaseService, ContextPageService, ContextService, RepoMapService
from app.context.repositories import ContextRepository
from app.settings.dependencies import build_settings_service


async def get_context_repository(db: AsyncSession = Depends(get_db)) -> ContextRepository:
    return ContextRepository(db)


async def build_context_service(db: AsyncSession) -> ContextService:
    project_service = await build_project_service(db)
    context_repo = ContextRepository(db)
    codebase_service = await build_codebase_service()
    return ContextService(
        project_service=project_service,
        context_repo=context_repo,
        codebase_service=codebase_service,
    )


async def get_context_service(
    db: AsyncSession = Depends(get_db),
) -> ContextService:
    return await build_context_service(db)


async def get_context_page_service(
    context_service: ContextService = Depends(get_context_service),
) -> ContextPageService:
    return ContextPageService(context_service=context_service)


async def build_codebase_service() -> CodebaseService:
    return CodebaseService()


async def build_repo_map_service(db: AsyncSession) -> RepoMapService:
    codebase_service = await build_codebase_service()
    context_service = await build_context_service(db)
    settings_service = await build_settings_service(db)
    return RepoMapService(
        codebase_service=codebase_service,
        context_service=context_service,
        settings_service=settings_service
    )