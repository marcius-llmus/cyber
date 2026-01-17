from async_lru import alru_cache
from sqlalchemy.ext.asyncio import AsyncSession

from app.llms.registry import LLMFactory
from app.llms.repositories import LLMSettingsRepository
from app.llms.services import LLMService


@alru_cache
async def build_llm_factory_instance() -> LLMFactory:
    return LLMFactory()


async def build_llm_service(db: AsyncSession) -> LLMService:
    llm_settings_repo = LLMSettingsRepository(db=db)
    llm_factory = await build_llm_factory_instance()
    return LLMService(llm_settings_repo=llm_settings_repo, llm_factory=llm_factory)
