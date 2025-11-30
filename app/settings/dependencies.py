from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.dependencies import get_db
from app.llms.factories import build_llm_factory_instance
from app.settings.repositories import LLMSettingsRepository, SettingsRepository
from app.settings.services import (
    LLMSettingsService,
    SettingsPageService,
    SettingsService,
)
from app.settings.factories import build_settings_service


async def get_llm_settings_repository(db: AsyncSession = Depends(get_db)) -> LLMSettingsRepository:
    return LLMSettingsRepository(db=db)


async def get_settings_repository(db: AsyncSession = Depends(get_db)) -> SettingsRepository:
    return SettingsRepository(db=db)


async def get_llm_settings_service(
    llm_settings_repo: LLMSettingsRepository = Depends(get_llm_settings_repository),
) -> LLMSettingsService:
    return LLMSettingsService(llm_settings_repo=llm_settings_repo)


async def get_settings_service(
    db: AsyncSession = Depends(get_db),
) -> SettingsService:
    return await build_settings_service(db)


async def get_settings_page_service(
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsPageService:
    llm_factory = await build_llm_factory_instance()
    return SettingsPageService(settings_service=settings_service, llm_factory=llm_factory)
