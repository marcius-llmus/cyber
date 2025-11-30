from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.dependencies import get_db
from app.context.services import ContextPageService, ContextService
from app.context.repositories import ContextRepository
from app.context.factories import build_context_service


async def get_context_repository(db: AsyncSession = Depends(get_db)) -> ContextRepository:
    return ContextRepository(db)


async def get_context_service(
    db: AsyncSession = Depends(get_db),
) -> ContextService:
    return await build_context_service(db)


async def get_context_page_service(
    context_service: ContextService = Depends(get_context_service),
) -> ContextPageService:
    return ContextPageService(context_service=context_service)
