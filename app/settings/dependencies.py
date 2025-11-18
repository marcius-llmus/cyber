from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.dependencies import get_db
from app.llms.dependencies import get_llm_factory
from app.llms.factory import LLMFactory
from app.settings.repositories import LLMSettingsRepository, SettingsRepository
from app.settings.services import (
    LLMSettingsService,
    SettingsPageService,
    SettingsService,
)


async def get_llm_settings_repository(db: AsyncSession = Depends(get_db)) -> LLMSettingsRepository:
    return LLMSettingsRepository(db=db)


async def get_settings_repository(db: AsyncSession = Depends(get_db)) -> SettingsRepository:
    return SettingsRepository(db=db)


async def get_llm_settings_service(
    llm_settings_repo: LLMSettingsRepository = Depends(get_llm_settings_repository),
) -> LLMSettingsService:
    return LLMSettingsService(llm_settings_repo=llm_settings_repo)


async def get_settings_service(
    settings_repo: SettingsRepository = Depends(get_settings_repository),
    llm_settings_service: LLMSettingsService = Depends(get_llm_settings_service),
    llm_factory: LLMFactory = Depends(get_llm_factory),
) -> SettingsService:
    return SettingsService(
        settings_repo=settings_repo,
        llm_settings_service=llm_settings_service,
        llm_factory=llm_factory,
    )


async def get_settings_page_service(
    settings_service: SettingsService = Depends(get_settings_service),
    llm_factory: LLMFactory = Depends(get_llm_factory),
) -> SettingsPageService:
    return SettingsPageService(settings_service=settings_service, llm_factory=llm_factory)