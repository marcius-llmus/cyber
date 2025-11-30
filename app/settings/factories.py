from sqlalchemy.ext.asyncio import AsyncSession
from app.llms.factories import build_llm_factory_instance
from app.settings.repositories import LLMSettingsRepository, SettingsRepository
from app.settings.services import (
    LLMSettingsService,
    SettingsService,
)


async def build_settings_service(db: AsyncSession) -> SettingsService:
    settings_repo = SettingsRepository(db=db)
    llm_settings_repo = LLMSettingsRepository(db=db)
    llm_settings_service = LLMSettingsService(llm_settings_repo=llm_settings_repo)
    llm_factory = await build_llm_factory_instance()
    
    return SettingsService(
        settings_repo=settings_repo,
        llm_settings_service=llm_settings_service,
        llm_factory=llm_factory,
    )
