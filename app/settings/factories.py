from sqlalchemy.ext.asyncio import AsyncSession

from app.llms.factory import LLMFactory
from app.settings.repositories import LLMSettingsRepository, SettingsRepository
from app.settings.services import LLMSettingsService, SettingsService


async def settings_service_factory(db: AsyncSession, llm_factory: LLMFactory) -> SettingsService:
    """Manually constructs the SettingsService stack."""
    settings_repo = SettingsRepository(db)
    llm_settings_repo = LLMSettingsRepository(db)
    llm_settings_service = LLMSettingsService(llm_settings_repo)
    return SettingsService(
        settings_repo=settings_repo,
        llm_settings_service=llm_settings_service,
        llm_factory=llm_factory,
    )
