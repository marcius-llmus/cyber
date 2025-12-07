from sqlalchemy.ext.asyncio import AsyncSession

from app.coder.patcher import PatcherService
from app.llms.factories import build_llm_service
from app.context.factories import build_workspace_service


async def build_patcher_service(db: AsyncSession) -> PatcherService:
    llm_service = await build_llm_service(db)
    context_service = await build_workspace_service(db)
    return PatcherService(
        llm_service=llm_service,
        context_service=context_service
    )
