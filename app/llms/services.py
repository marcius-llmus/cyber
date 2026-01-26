import functools
import logging
from decimal import Decimal

from async_lru import alru_cache
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.llms.openai import OpenAI
from llama_index_instrumentation.dispatcher import instrument_tags

from app.core.config import settings
from app.llms.enums import LLMModel, LLMProvider, LLMRole
from app.llms.exceptions import MissingLLMApiKeyException
from app.llms.models import LLMSettings
from app.llms.registry import LLMFactory
from app.llms.repositories import LLMSettingsRepository
from app.llms.schemas import LLM
from app.settings.exceptions import (
    ContextWindowExceededException,
    LLMSettingsNotFoundException,
)
from app.settings.schemas import LLMSettingsUpdate

logger = logging.getLogger(__name__)


def instrument_generator(func):
    """Decorator that wraps the result of an async generator factory with instrumentation tags."""

    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        # 1. Await the original method to get the actual generator
        stream = await func(self, *args, **kwargs)

        # 2. Wrap the iteration in the instrumentation context
        async def wrapped_gen():
            with instrument_tags(self._get_instrumentation_tags()):
                async for item in stream:
                    yield item

        # 3. Return the wrapped generator (matching the original return type)
        return wrapped_gen()

    return wrapper


class InstrumentedLLMMixin:
    """Helper to generate instrumentation tags."""

    _provider_id: str
    _api_flavor: str
    model: str

    def _get_instrumentation_tags(self) -> dict:
        return {
            "__provider_id__": self._provider_id,
            "__model_name__": self.model,
            "__api_flavor__": self._api_flavor,
        }

    async def achat(self, *args, **kwargs):
        with instrument_tags(self._get_instrumentation_tags()):
            return await super().achat(*args, **kwargs)  # noqa

    @instrument_generator
    async def astream_chat(self, *args, **kwargs):
        return await super().astream_chat(*args, **kwargs)  # noqa


class InstrumentedOpenAI(InstrumentedLLMMixin, OpenAI):
    _provider_id: str = "openai"
    _api_flavor: str = "chat"


class InstrumentedAnthropic(InstrumentedLLMMixin, Anthropic):
    _provider_id: str = "anthropic"
    _api_flavor: str = "default"


class InstrumentedGoogleGenAI(InstrumentedLLMMixin, GoogleGenAI):
    _provider_id: str = "google"
    _api_flavor: str = "default"


class LLMService:
    def __init__(
        self, llm_settings_repo: LLMSettingsRepository, llm_factory: LLMFactory
    ):
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
            raise LLMSettingsNotFoundException(
                f"LLMSettings for model {model_name} not found."
            )
        return db_obj

    async def get_coding_llm(self) -> LLMSettings:
        """Returns the LLM currently assigned the CODER role."""
        db_obj = await self.llm_settings_repo.get_by_role(LLMRole.CODER)

        if not db_obj:
            logger.warning(
                "No LLM assigned as CODER. Attempting to set default (GPT-4.1-mini)."
            )
            # let's make default gpt_4_1 explicitly o.o
            # I am not an openai fanboy, but gemini is too unstable xdd
            db_obj = await self.llm_settings_repo.get_by_model_name(
                LLMModel.GPT_4_1_MINI
            )

            if not db_obj:
                raise LLMSettingsNotFoundException(
                    "No LLM is currently assigned as the Coder and no models available."
                )

            return await self.update_coding_llm(db_obj.id, LLMSettingsUpdate())

        return db_obj

    async def update_settings(
        self, llm_id: int, settings_in: LLMSettingsUpdate
    ) -> LLMSettings:
        db_obj = await self.llm_settings_repo.get(llm_id)
        if not db_obj:
            raise LLMSettingsNotFoundException(
                f"LLMSettings with id {llm_id} not found."
            )

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

    async def update_coding_llm(
        self, llm_id: int, settings_in: LLMSettingsUpdate
    ) -> LLMSettings:
        """
        Promotes the specified LLM to the CODER role and updates its configuration.
        """
        await self.llm_settings_repo.set_active_role(llm_id=llm_id, role=LLMRole.CODER)
        return await self.update_settings(llm_id=llm_id, settings_in=settings_in)

    async def get_client(
        self, model_name: LLMModel, temperature: Decimal
    ) -> OpenAI | Anthropic | GoogleGenAI:
        """
        Hydrates a client using internal configuration.
        """
        temperature = float(temperature)
        llm_metadata = await self.llm_factory.get_llm(model_name)
        api_key = await self.llm_settings_repo.get_api_key_for_provider(
            llm_metadata.provider
        )

        if not api_key:
            raise MissingLLMApiKeyException(
                f"Missing API key for provider {llm_metadata.provider}. Please configure it in settings."
            )

        return await self._get_client_instance(model_name, temperature, api_key)

    @alru_cache
    async def _get_client_instance(
        self, model_name: LLMModel, temperature: float, api_key: str
    ):
        llm_metadata = await self.llm_factory.get_llm(model_name)
        provider = llm_metadata.provider

        if provider == LLMProvider.OPENAI:
            return InstrumentedOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=api_key,
                timeout=settings.LLM_TIMEOUT,
                additional_kwargs={"stream_options": {"include_usage": True}},
            )
        elif provider == LLMProvider.ANTHROPIC:
            return InstrumentedAnthropic(
                model=model_name,
                temperature=temperature,
                api_key=api_key,
                timeout=settings.LLM_TIMEOUT,
            )
        elif provider == LLMProvider.GOOGLE:
            return InstrumentedGoogleGenAI(
                model=model_name,
                temperature=temperature,
                api_key=api_key,
                timeout=settings.LLM_TIMEOUT,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
