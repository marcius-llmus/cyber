from functools import lru_cache
from genai_prices import UpdatePrices
from sqlalchemy.ext.asyncio import AsyncSession
from app.usage.repositories import UsageRepository, GlobalUsageRepository
from app.usage.services import UsageService
from app.llms.factories import get_llm_factory_instance
from app.settings.dependencies import build_settings_service


async def build_usage_service(db: AsyncSession) -> UsageService:
    usage_repo = UsageRepository(db=db)
    global_repo = GlobalUsageRepository(db=db)
    llm_factory = await get_llm_factory_instance()
    settings_service = await build_settings_service(db)
    return UsageService(
        usage_repo=usage_repo,
        global_usage_repo=global_repo,
        llm_factory=llm_factory,
        settings_service=settings_service
    )

@lru_cache
def get_price_updater() -> UpdatePrices:
    return UpdatePrices()
