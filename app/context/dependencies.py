from fastapi import Depends

from app.projects.dependencies import get_project_service
from app.projects.services import ProjectService
from app.context.services import ContextPageService, ContextService


async def get_context_service(
    project_service: ProjectService = Depends(get_project_service),
) -> ContextService:
    return ContextService(project_service=project_service)


async def get_context_page_service(
    context_service: ContextService = Depends(get_context_service),
) -> ContextPageService:
    return ContextPageService(context_service=context_service)