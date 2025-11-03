from app.llms.enums import LLMModel, LLMProvider
from app.llms.factory import LLMFactory
from app.settings.exceptions import LLMSettingsAlreadyExistsException
from app.settings.models import LLMSettings, Settings
from app.settings.repositories import LLMSettingsRepository, SettingsRepository
from app.settings.exceptions import ContextWindowExceededException, LLMSettingsNotFoundException, SettingsNotFoundException
from app.settings.schemas import LLMSettingsCreate, SettingsUpdate


class LLMSettingsService:
    def __init__(self, llm_settings_repo: LLMSettingsRepository):
        self.llm_settings_repo = llm_settings_repo

    def get_by_name(self, model_name: str) -> LLMSettings:
        db_obj = self.llm_settings_repo.get_by_model_name(model_name)
        if not db_obj:
            raise LLMSettingsNotFoundException(f"LLMSettings for model {model_name} not found.")
        return db_obj

    def create(self, settings_in: LLMSettingsCreate) -> LLMSettings:
        if self.llm_settings_repo.get_by_model_name(settings_in.model_name):
            raise LLMSettingsAlreadyExistsException(f"LLMSettings for model {settings_in.model_name} already exists.")
        return self.llm_settings_repo.create(obj_in=settings_in)

    def get_api_key_for_provider(self, provider: LLMProvider) -> str | None:
        llm_setting_with_key = (
            self.llm_settings_repo.db.query(LLMSettings)
            .filter(LLMSettings.provider == provider, LLMSettings.api_key.isnot(None))
            .first()
        )
        return llm_setting_with_key.api_key if llm_setting_with_key else None


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

    def get_settings(self) -> Settings:
        settings = self.settings_repo.get(pk=1)
        if not settings:
            # This should not happen if the startup hook is successful
            raise SettingsNotFoundException("Application settings have not been initialized.")
        return settings

    def update_settings(self, *, settings_in: SettingsUpdate) -> Settings:
        settings = self.get_settings()

        if settings_in.coding_llm_settings:
            llm_update_payload = settings_in.coding_llm_settings
            current_llm_settings = settings.coding_llm_settings

            if llm_update_payload.model_name and llm_update_payload.model_name != current_llm_settings.model_name:
                target_llm_settings = self.llm_settings_service.get_by_name(llm_update_payload.model_name)
                settings.coding_llm_settings_id = target_llm_settings.id
                current_llm_settings = target_llm_settings

            if llm_update_payload.context_window is not None:
                model_meta = self.llm_factory.get_llm(LLMModel(current_llm_settings.model_name))
                if llm_update_payload.context_window > model_meta.default_context_window:
                    raise ContextWindowExceededException(
                        f"Context window for {current_llm_settings.model_name} "
                        f"cannot exceed {model_meta.default_context_window} tokens."
                    )

            # Update the individual setting for context_window, etc.
            self.llm_settings_service.llm_settings_repo.update(
                db_obj=current_llm_settings, obj_in=llm_update_payload
            )
            # Update API key for all models from the same provider
            self.llm_settings_service.llm_settings_repo.update_api_key_for_provider(
                provider=current_llm_settings.provider, api_key=llm_update_payload.api_key
            )

        return self.settings_repo.update(db_obj=settings, obj_in=settings_in)


class SettingsPageService:
    def __init__(self, settings_service: SettingsService, llm_factory: LLMFactory):
        self.settings_service = settings_service
        self.llm_factory = llm_factory

    def get_settings_page_data(self) -> dict:
        settings = self.settings_service.get_settings()
        all_llms = self.llm_factory.get_all_llms()
        llm_model_providers = {llm.model_name: llm.provider.value for llm in all_llms}
        return {"settings": settings, "llm_model_providers": llm_model_providers}

    def get_api_key_input_data(self, model_name: str) -> dict:
        llm_meta = self.llm_factory.get_llm(LLMModel(model_name))
        provider = llm_meta.provider
        api_key = self.settings_service.llm_settings_service.get_api_key_for_provider(provider)
        return {"provider": provider.value, "api_key": api_key}
