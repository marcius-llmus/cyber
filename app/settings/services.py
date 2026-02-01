from app.llms.services import LLMService
from app.settings.constants import API_KEY_MASK
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

        # we save everytime, even if it didn't really change, for simplicity
        # if that was not the case, others params like reasoning would not be saved if llm didn't change
        # I will keep this if check only for pattern, but it msut always be saved
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
        coding_llm_masked_api_key = await self._get_masked_key_or_empty(
            current_coder.provider
        )

        return {
            "settings": settings,
            "current_coder": current_coder,
            "llm_options": llm_options,
            "coding_llm_masked_api_key": coding_llm_masked_api_key,
        }

    async def get_llm_dependent_fields_data_by_id(self, llm_id: int) -> dict:
        llm_settings = await self.llm_service.llm_settings_repo.get(llm_id)
        masked_api_key = await self._get_masked_key_or_empty(llm_settings.provider)
        return {
            "provider": llm_settings.provider.value,
            "api_key": masked_api_key,
            "current_coder": llm_settings,
        }

    async def _get_masked_key_or_empty(self, provider):
        coder_api_key = (
            await self.llm_service.llm_settings_repo.get_api_key_for_provider(provider)
        )
        masked_coder_api_key = API_KEY_MASK if coder_api_key else ""
        return masked_coder_api_key
