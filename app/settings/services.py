from app.llms.enums import LLMModel, LLMProvider
from sqlalchemy import select
from app.llms.factories import LLMFactory
from app.settings.exceptions import LLMSettingsAlreadyExistsException
from app.settings.models import LLMSettings, Settings
from app.settings.repositories import LLMSettingsRepository, SettingsRepository
from app.settings.exceptions import ContextWindowExceededException, LLMSettingsNotFoundException, SettingsNotFoundException
from app.settings.schemas import (
    LLMSettingsCreate,
    LLMSettingsUpdate,
    SettingsUpdate,
)


class LLMSettingsService:
    def __init__(self, llm_settings_repo: LLMSettingsRepository):
        self.llm_settings_repo = llm_settings_repo

    async def get_by_name(self, model_name: str) -> LLMSettings:
        db_obj = await self.llm_settings_repo.get_by_model_name(model_name)
        if not db_obj:
            raise LLMSettingsNotFoundException(f"LLMSettings for model {model_name} not found.")
        return db_obj

    async def create(self, settings_in: LLMSettingsCreate) -> LLMSettings:
        if await self.llm_settings_repo.get_by_model_name(settings_in.model_name):
            raise LLMSettingsAlreadyExistsException(f"LLMSettings for model {settings_in.model_name} already exists.")
        return await self.llm_settings_repo.create(obj_in=settings_in)

    async def get_api_key_for_provider(self, provider: LLMProvider) -> str | None:
        llm_setting_with_key = (
            await self.llm_settings_repo.db.execute(
                select(LLMSettings).filter(LLMSettings.provider == provider, LLMSettings.api_key.isnot(None)).limit(1)
            )
        )
        if settings := llm_setting_with_key.scalars().first():
            return settings.api_key

        return None

    async def update(self, db_obj: LLMSettings, obj_in: LLMSettingsUpdate) -> LLMSettings:
        return await self.llm_settings_repo.update(db_obj=db_obj, obj_in=obj_in)

    async def update_api_key_for_provider(self, provider: LLMProvider, api_key: str | None) -> None:
        return await self.llm_settings_repo.update_api_key_for_provider(provider=provider, api_key=api_key)


class SettingsService:
    def __init__(
        self,
        settings_repo: SettingsRepository,
        llm_settings_service: LLMSettingsService,
        llm_factory: LLMFactory,
    ):
        self.settings_repo = settings_repo
        self.llm_settings_service = llm_settings_service
        self.llm_factory = llm_factory

    async def get_settings(self) -> Settings:
        settings = await self.settings_repo.get(pk=1)
        if not settings:
            # This should not happen if the startup hook is successful
            raise SettingsNotFoundException("Application settings have not been initialized.")
        return settings

    async def update_settings(self, *, settings_in: SettingsUpdate) -> Settings:
        settings = await self.get_settings()

        if settings_in.coding_llm_settings:
            llm_update_payload = settings_in.coding_llm_settings
            current_llm_settings = settings.coding_llm_settings

            if llm_update_payload.model_name and llm_update_payload.model_name != current_llm_settings.model_name:
                target_llm_settings = await self.llm_settings_service.get_by_name(llm_update_payload.model_name)
                settings.coding_llm_settings_id = target_llm_settings.id
                current_llm_settings = target_llm_settings

            if llm_update_payload.context_window is not None:
                model_meta = await self.llm_factory.get_llm(LLMModel(current_llm_settings.model_name))
                if llm_update_payload.context_window > model_meta.default_context_window:
                    raise ContextWindowExceededException(
                        f"Context window for {current_llm_settings.model_name} "
                        f"cannot exceed {model_meta.default_context_window} tokens."
                    )

            # Update the individual setting for context_window, etc.
            await self.llm_settings_service.update(db_obj=current_llm_settings, obj_in=llm_update_payload)
            # Update API key for all models from the same provider
            await self.llm_settings_service.update_api_key_for_provider(
                provider=current_llm_settings.provider, api_key=llm_update_payload.api_key
            )

        return await self.settings_repo.update(db_obj=settings, obj_in=settings_in)


class SettingsPageService:
    def __init__(self, settings_service: SettingsService, llm_factory: LLMFactory):
        self.settings_service = settings_service
        self.llm_factory = llm_factory

    async def get_settings_page_data(self) -> dict:
        settings = await self.settings_service.get_settings()
        all_llms = await self.llm_factory.get_all_llms()
        llm_model_providers = {llm.model_name: llm.provider.value for llm in all_llms}
        return {"settings": settings, "llm_model_providers": llm_model_providers}

    async def get_api_key_input_data(self, model_name: str) -> dict:
        llm_meta = await self.llm_factory.get_llm(LLMModel(model_name))
        provider = llm_meta.provider
        api_key = await self.settings_service.llm_settings_service.get_api_key_for_provider(provider)
        return {"provider": provider.value, "api_key": api_key}
