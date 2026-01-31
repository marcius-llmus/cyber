from app.llms.services import LLMService
from app.settings.exceptions import SettingsNotFoundException
from app.settings.models import Settings
from app.settings.repositories import SettingsRepository
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
            raise SettingsNotFoundException(
                "Application settings have not been initialized."
            )
        return settings

    async def update_settings(self, *, settings_in: SettingsUpdate) -> Settings:
        db_obj = await self.get_settings()

        if settings_in.coding_llm_settings:
            # We treat the ID passed in the schema as the one to promote to CODER
            await self.llm_service.update_coding_llm(
                llm_id=settings_in.coding_llm_settings_id,
                settings_in=settings_in.coding_llm_settings,
            )

        return await self.settings_repo.update(db_obj=db_obj, obj_in=settings_in)


class SettingsPageService:
    def __init__(self, settings_service: SettingsService, llm_service: LLMService):
        self.settings_service = settings_service
        self.llm_service = llm_service

    async def get_settings_page_data(self) -> dict:
        settings = await self.settings_service.get_settings()
        # Fetch actual DB records to get IDs
        current_coder = await self.llm_service.get_coding_llm()
        llm_options = await self.llm_service.get_all_llm_settings()

        return {
            "settings": settings,
            "current_coder": current_coder,
            "llm_options": llm_options,
        }

    async def get_llm_dependent_fields_data_by_id(self, llm_id: int) -> dict:
        llm_settings = await self.llm_service.llm_settings_repo.get(llm_id)
        api_key = await self.llm_service.llm_settings_repo.get_api_key_for_provider(
            llm_settings.provider
        )
        return {
            "provider": llm_settings.provider.value,
            "api_key": api_key,
            "current_coder": llm_settings,
        }
