from sqlalchemy.ext.asyncio import AsyncSession

from app.context.services import ContextService
from app.projects.repositories import ProjectRepository
from app.projects.services import ProjectService


async def context_service_factory(session: AsyncSession) -> ContextService:
    """Manually constructs the ContextService stack."""
    project_repo = ProjectRepository(session)
    project_service = ProjectService(project_repo)
    return ContextService(project_service=project_service)
