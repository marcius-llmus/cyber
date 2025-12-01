from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.factories import build_project_service
from app.context.services import CodebaseService, ContextService, RepoMapService
from app.context.repositories import ContextRepository
from app.settings.factories import build_settings_service


async def build_context_service(db: AsyncSession) -> ContextService:
    project_service = await build_project_service(db)
    context_repo = ContextRepository(db)
    codebase_service = await build_codebase_service()
    return ContextService(
        project_service=project_service,
        context_repo=context_repo,
        codebase_service=codebase_service,
    )

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
