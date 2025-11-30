from app.llms.enums import LLMModel
from app.llms.factories import LLMFactory
from app.settings.services import SettingsService


class LLMService:
    def __init__(self, settings_service: SettingsService, llm_factory: LLMFactory):
        self.settings_service = settings_service
        self.llm_factory = llm_factory

    async def get_coding_llm(self) -> any:
        """
        Orchestrates the creation of the coding LLM client.
        Fetches settings, resolves the API key, and hydrates the client.
        """
        # 1. Get Global Settings
        settings = await self.settings_service.get_settings()
        model_name = LLMModel(settings.coding_llm_settings.model_name)

        # 2. Get Metadata to find the Provider
        llm_metadata = await self.llm_factory.get_llm(model_name)

        # 3. Get the specific API Key for that Provider
        api_key = await self.settings_service.llm_settings_service.get_api_key_for_provider(
            llm_metadata.provider
        )

        # 4. Return the hydrated client
        return await self.llm_factory.get_client(
            model_name=model_name,
            temperature=settings.coding_llm_temperature,
            api_key=api_key,
        )
