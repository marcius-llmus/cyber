from typing import Union
from async_lru import alru_cache
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.llms.openai import OpenAI

from app.llms.schemas import LLM
from app.llms.enums import LLMModel, LLMProvider
from app.llms.registry import LLMFactory
from app.llms.repositories import LLMSettingsRepository
from app.llms.models import LLMSettings
from app.settings.schemas import LLMSettingsUpdate
from app.settings.exceptions import ContextWindowExceededException, LLMSettingsNotFoundException


class LLMService:
    def __init__(self, llm_settings_repo: LLMSettingsRepository, llm_factory: LLMFactory):
        self.llm_settings_repo = llm_settings_repo
        self.llm_factory = llm_factory

    async def get_model_metadata(self, model_name: LLMModel) -> LLM:
        return await self.llm_factory.get_llm(model_name)

    async def get_all_models(self) -> list[LLM]:
        return await self.llm_factory.get_all_llms()

    async def get_all_llm_settings(self) -> list[LLMSettings]:
        return await self.llm_settings_repo.get_all()

    async def get_llm_settings(self, model_name: str) -> LLMSettings:
        db_obj = await self.llm_settings_repo.get_by_model_name(model_name)
        if not db_obj:
            raise LLMSettingsNotFoundException(f"LLMSettings for model {model_name} not found.")
        return db_obj


    async def update_settings(self, llm_id: int, settings_in: LLMSettingsUpdate) -> LLMSettings:
        db_obj = await self.llm_settings_repo.get(llm_id)
        if not db_obj:
            raise LLMSettingsNotFoundException(f"LLMSettings with id {llm_id} not found.")

        # Validate Context Window
        if settings_in.context_window is not None:
            model_meta = await self.llm_factory.get_llm(LLMModel(db_obj.model_name))
            if settings_in.context_window > model_meta.default_context_window:
                raise ContextWindowExceededException(
                    f"Context window cannot exceed {model_meta.default_context_window} tokens."
                )

        if settings_in.api_key is not None:
             await self.llm_settings_repo.update_api_key_for_provider(
                provider=db_obj.provider, api_key=settings_in.api_key
            )

        return await self.llm_settings_repo.update(db_obj=db_obj, obj_in=settings_in)

    async def get_client(self, model_name: LLMModel, temperature: float) -> Union[OpenAI, Anthropic, GoogleGenAI]:
        """
        Hydrates a client using internal configuration.
        """
        llm_metadata = await self.llm_factory.get_llm(model_name)
        api_key = await self.llm_settings_repo.get_api_key_for_provider(llm_metadata.provider)
        
        return await self._get_client_instance(model_name, temperature, api_key)

    @alru_cache
    async def _get_client_instance(self, model_name: LLMModel, temperature: float, api_key: str):
        llm_metadata = await self.llm_factory.get_llm(model_name)
        provider = llm_metadata.provider

        if provider == LLMProvider.OPENAI:
            return OpenAI(model=model_name, temperature=temperature, api_key=api_key)
        elif provider == LLMProvider.ANTHROPIC:
            return Anthropic(model=model_name, temperature=temperature, api_key=api_key)
        elif provider == LLMProvider.GOOGLE:
            return GoogleGenAI(model=model_name, temperature=temperature, api_key=api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
