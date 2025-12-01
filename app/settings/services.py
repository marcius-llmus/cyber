from app.llms.enums import LLMModel
from app.llms.services import LLMService
from app.settings.models import Settings
from app.settings.repositories import SettingsRepository
from app.settings.exceptions import SettingsNotFoundException
from app.settings.schemas import SettingsUpdate


class SettingsService:
    def __init__(
        self,
        settings_repo: SettingsRepository,
        llm_service: LLMService,
    ):
        self.settings_repo = settings_repo
        self.llm_service = llm_service

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
            
            # Delegate logic to LLM Service
            updated_llm_settings = await self.llm_service.update_configuration(
                obj_in=llm_update_payload
            )
            
            # Update pointer if changed
            if updated_llm_settings.id != settings.coding_llm_settings_id:
                settings.coding_llm_settings_id = updated_llm_settings.id

        return await self.settings_repo.update(db_obj=settings, obj_in=settings_in)


class SettingsPageService:
    def __init__(self, settings_service: SettingsService, llm_service: LLMService):
        self.settings_service = settings_service
        self.llm_service = llm_service

    async def get_settings_page_data(self) -> dict:
        settings = await self.settings_service.get_settings()
        all_llms = await self.llm_service.get_all_models()
        llm_model_providers = {llm.model_name: llm.provider.value for llm in all_llms}
        return {"settings": settings, "llm_model_providers": llm_model_providers}

    async def get_api_key_input_data(self, model_name: str) -> dict:
        llm_meta = await self.llm_service.get_model_metadata(LLMModel(model_name))
        provider = llm_meta.provider
        api_key = await self.llm_service.llm_settings_repo.get_api_key_for_provider(provider)
        return {"provider": provider.value, "api_key": api_key}