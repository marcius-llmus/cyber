from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.dependencies import get_db
from app.llms.factories import build_llm_service
from app.settings.factories import build_settings_service
from app.settings.repositories import SettingsRepository
from app.settings.services import SettingsPageService, SettingsService


async def get_settings_repository(
    db: AsyncSession = Depends(get_db),
) -> SettingsRepository:
    return SettingsRepository(db=db)


async def get_settings_service(
    db: AsyncSession = Depends(get_db),
) -> SettingsService:
    return await build_settings_service(db)


async def get_settings_page_service(
    settings_service: SettingsService = Depends(get_settings_service),
    db: AsyncSession = Depends(get_db),
) -> SettingsPageService:
    llm_service = await build_llm_service(db)
    return SettingsPageService(
        settings_service=settings_service, llm_service=llm_service
    )
