from sqlalchemy.ext.asyncio import AsyncSession

from app.llms.factories import build_llm_service
from app.settings.repositories import SettingsRepository
from app.settings.services import SettingsService


async def build_settings_service(db: AsyncSession) -> SettingsService:
    settings_repo = SettingsRepository(db=db)
    llm_service = await build_llm_service(db)

    return SettingsService(
        settings_repo=settings_repo,
        llm_service=llm_service,
    )
