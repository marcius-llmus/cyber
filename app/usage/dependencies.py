from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.commons.dependencies import get_db
from app.usage.services import UsagePageService, UsageService
from app.usage.factories import build_usage_service


async def get_usage_service(db: AsyncSession = Depends(get_db)) -> UsageService:
    return await build_usage_service(db)


async def get_usage_page_service(
    session_id: int = 0,
    usage_service: UsageService = Depends(get_usage_service),
) -> UsagePageService:
    return UsagePageService(usage_service=usage_service, session_id=session_id)
