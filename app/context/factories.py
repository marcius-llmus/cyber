from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.factories import build_project_service
from app.context.services import WorkspaceService, RepoMapService, SearchService, FileSystemService
from app.context.services.codebase import CodebaseService
from app.context.repositories import ContextRepository
from app.settings.factories import build_settings_service


async def build_workspace_service(db: AsyncSession) -> WorkspaceService:
    project_service = await build_project_service(db)
    context_repo = ContextRepository(db)
    codebase_service = await build_codebase_service()
    return WorkspaceService(
        project_service=project_service,
        context_repo=context_repo,
        codebase_service=codebase_service,
    )

async def build_codebase_service() -> CodebaseService:
    return CodebaseService()


async def build_repo_map_service(db: AsyncSession) -> RepoMapService:
    context_service = await build_workspace_service(db)
    codebase_service = await build_codebase_service()
    settings_service = await build_settings_service(db)
    return RepoMapService(
        context_service=context_service,
        codebase_service=codebase_service,
        settings_service=settings_service
    )

async def build_search_service(db: AsyncSession) -> SearchService:
    project_service = await build_project_service(db)
    codebase_service = await build_codebase_service()
    settings_service = await build_settings_service(db)
    return SearchService(
        project_service=project_service, 
        codebase_service=codebase_service,
        settings_service=settings_service
    )


async def build_filesystem_service(db: AsyncSession) -> FileSystemService:
    project_service = await build_project_service(db)
    codebase_service = await build_codebase_service()
    return FileSystemService(project_service=project_service, codebase_service=codebase_service)
