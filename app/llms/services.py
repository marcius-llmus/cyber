import functools
import logging
from decimal import Decimal
from typing import Any, Optional, Literal

from async_lru import alru_cache
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.llms.openai import OpenAI
from llama_index_instrumentation.dispatcher import instrument_tags
from pydantic import BaseModel, ValidationError, Field

from app.core.config import settings
from app.llms.enums import LLMModel, LLMProvider, LLMRole
from app.llms.exceptions import (
    InvalidLLMReasoningConfigException,
    MissingLLMApiKeyException,
)
from app.llms.models import LLMSettings
from app.llms.registry import LLMFactory
from app.llms.repositories import LLMSettingsRepository
from app.llms.schemas import (
    LLM,
    AnthropicReasoningConfig,
    GoogleReasoningConfig,
    OpenAIReasoningConfig,
)
from app.settings.constants import API_KEY_MASK
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
        stream = await func(self, *args, **kwargs)

        async def wrapped_gen():
            with instrument_tags(self._get_instrumentation_tags()):
                async for item in stream:
                    yield item

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
    reasoning_effort: Optional[Literal["none", "low", "medium", "high", "xhigh"]] = Field(
        default=None,
        description="The effort to use for reasoning models.",
    )
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

        if settings_in.api_key is not None and not self._is_api_key_mask(
            settings_in.api_key
        ):
            await self.llm_settings_repo.update_api_key_for_provider(
                provider=db_obj.provider, api_key=settings_in.api_key
            )

        if settings_in.reasoning_config is not None:
            try:
                reasoning_config = self._validate_reasoning_config(
                    provider=db_obj.provider,
                    reasoning_config=settings_in.reasoning_config,
                )
            except (ValidationError, InvalidLLMReasoningConfigException) as e:
                raise InvalidLLMReasoningConfigException(
                    f"Invalid reasoning_config for provider={db_obj.provider}: {e}"
                ) from e

            await self.llm_settings_repo.update_reasoning_config_for_provider(
                provider=db_obj.provider,
                reasoning_config=reasoning_config,
            )

        return await self.llm_settings_repo.update(db_obj=db_obj, obj_in=settings_in)

    @staticmethod
    def _is_api_key_mask(value: str) -> bool:
        return value == API_KEY_MASK

    @staticmethod
    def _validate_reasoning_config(
        provider: LLMProvider, reasoning_config: dict[str, Any]
    ) -> dict[str, Any]:
        schema: type[BaseModel] | None = {
            LLMProvider.OPENAI: OpenAIReasoningConfig,
            LLMProvider.ANTHROPIC: AnthropicReasoningConfig,
            LLMProvider.GOOGLE: GoogleReasoningConfig,
        }.get(provider)

        if schema is None:
            raise InvalidLLMReasoningConfigException(
                f"Invalid reasoning_config for provider={provider}: unsupported provider"
            )

        model = schema.model_validate(reasoning_config)
        return model.model_dump()

    async def update_coding_llm(
        self, llm_id: int, settings_in: LLMSettingsUpdate
    ) -> LLMSettings:
        """
        Promotes the specified LLM to the CODER role and updates its configuration.
        """
        await self.llm_settings_repo.set_active_role(llm_id=llm_id, role=LLMRole.CODER)
        return await self.update_settings(llm_id=llm_id, settings_in=settings_in)

    async def get_client(
        self,
        model_name: LLMModel,
        temperature: Decimal,
        reasoning_config: dict[str, Any],
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

        # note: small hack. we freeze the dict so the alru_cache keeps working
        # even with the addition of more variables like reasoning params, it still worth caching
        frozen_reasoning_config = self._freeze_reasoning_config(reasoning_config)

        return await self._get_client_instance(
            model_name, temperature, api_key, frozen_reasoning_config
        )

    @staticmethod
    def _freeze_reasoning_config(
        reasoning_config: dict[str, Any] | None,
    ) -> tuple[tuple[str, Any], ...] | None:
        if to_freeze_reasoning_config := reasoning_config:
            return tuple(sorted(to_freeze_reasoning_config.items()))
        return None

    @alru_cache
    async def _get_client_instance(
        self,
        model_name: LLMModel,
        temperature: float,
        api_key: str,
        reasoning_config: tuple[tuple[str, Any], ...] | None = None,
    ):
        llm_metadata = await self.llm_factory.get_llm(model_name)
        provider = llm_metadata.provider
        effective_reasoning = (
            dict(reasoning_config) if reasoning_config else llm_metadata.reasoning
        )

        if provider == LLMProvider.OPENAI:
            additional_kwargs = {"stream_options": {"include_usage": True}}
            return InstrumentedOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=api_key,
                timeout=settings.LLM_TIMEOUT,
                **effective_reasoning,
                additional_kwargs=additional_kwargs,
            )
        elif provider == LLMProvider.ANTHROPIC:
            return InstrumentedAnthropic(
                model=model_name,
                temperature=temperature,
                api_key=api_key,
                timeout=settings.LLM_TIMEOUT,
                **effective_reasoning,
            )
        elif provider == LLMProvider.GOOGLE:
            return InstrumentedGoogleGenAI(
                model=model_name,
                temperature=temperature,
                api_key=api_key,
                timeout=settings.LLM_TIMEOUT,
                **effective_reasoning,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
