from app.llms.services import LLMService
from app.settings.exceptions import SettingsNotFoundException
from app.settings.models import Settings
from app.settings.repositories import SettingsRepository
from app.settings.schemas import LLMSettingsReadPublic, SettingsUpdate


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

    # todo: usually, we return the db obj. here, we are transforming to pydantic
    #       in json requests, we declare the schema obj in the model and return the db to router
    #       the router will get the db obj and serialize automatically with the from orm
    #       we are mostly using htmx. htmx is using the db obj directly and there should be a pattern
    #       pages services should return pydantic? should the htmx view convert? but the api key must not
    #       be returned. then it is a business logic, but business logic doesn't live in routes, so whta?
    #       currently, it is ok it is considered a service, even that it is a 'page' service, for formatting.
    #       but we must make sure that things like changing or requesting api key is resolved at a true service
    async def _to_public_llm_settings(self, llm_settings) -> LLMSettingsReadPublic:
        api_key = await self.llm_service.llm_settings_repo.get_api_key_for_provider(
            llm_settings.provider
        )
        return LLMSettingsReadPublic(
            id=llm_settings.id,
            model_name=llm_settings.model_name,
            context_window=llm_settings.context_window,
            provider=llm_settings.provider,
            visual_name=llm_settings.visual_name,
            reasoning_config=llm_settings.reasoning_config,
            api_key_present=bool(api_key),
        )

    async def get_settings_page_data(self) -> dict:
        settings = await self.settings_service.get_settings()
        # Fetch actual DB records to get IDs
        current_coder_db = await self.llm_service.get_coding_llm()
        llm_options_db = await self.llm_service.get_all_llm_settings()

        current_coder = await self._to_public_llm_settings(current_coder_db)
        llm_options = [await self._to_public_llm_settings(x) for x in llm_options_db]

        return {
            "settings": settings,
            "current_coder": current_coder,
            "llm_options": llm_options,
        }

    async def get_llm_dependent_fields_data_by_id(self, llm_id: int) -> dict:
        llm_settings_db = await self.llm_service.llm_settings_repo.get(llm_id)
        llm_settings = await self._to_public_llm_settings(llm_settings_db)
        return {
            "provider": llm_settings.provider,
            "api_key": llm_settings.api_key,
            "current_coder": llm_settings,
        }
