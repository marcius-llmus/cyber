from functools import lru_cache

from genai_prices import UpdatePrices
from sqlalchemy.ext.asyncio import AsyncSession

from app.llms.factories import build_llm_service
from app.settings.factories import build_settings_service
from app.usage.repositories import GlobalUsageRepository, UsageRepository
from app.usage.services import UsageService


async def build_usage_service(db: AsyncSession) -> UsageService:
    usage_repo = UsageRepository(db=db)
    global_repo = GlobalUsageRepository(db=db)
    llm_service = await build_llm_service(db)
    settings_service = await build_settings_service(db)
    return UsageService(
        usage_repo=usage_repo,
        global_usage_repo=global_repo,
        llm_service=llm_service,
        settings_service=settings_service,
    )


@lru_cache
def build_price_updater() -> UpdatePrices:
    return UpdatePrices()
