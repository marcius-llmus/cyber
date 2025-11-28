from sqlalchemy.ext.asyncio import AsyncSession

from app.coder.patcher import PatcherService
from app.llms.dependencies import build_llm_service
from app.projects.dependencies import build_project_service


async def build_patcher_service(db: AsyncSession) -> PatcherService:
    llm_service = await build_llm_service(db)
    project_service = await build_project_service(db)
    return PatcherService(llm_service=llm_service, project_service=project_service)
