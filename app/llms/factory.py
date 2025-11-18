from typing import Union

from async_lru import alru_cache

from llama_index.llms.anthropic import Anthropic
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.llms.openai import OpenAI

from app.llms.domain import LLM
from app.llms.enums import LLMModel, LLMProvider




class LLMFactory:
    _MODEL_REGISTRY: dict[LLMModel, LLM] = {
        # Anthropic
        LLMModel.CLAUDE_SONNET_4_5: LLM(
            model_name=LLMModel.CLAUDE_SONNET_4_5, provider=LLMProvider.ANTHROPIC, default_context_window=200000
        ),
        LLMModel.CLAUDE_OPUS_4_1: LLM(
            model_name=LLMModel.CLAUDE_OPUS_4_1, provider=LLMProvider.ANTHROPIC, default_context_window=200000
        ),
        # Google
        LLMModel.GEMINI_2_5_PRO: LLM(
            model_name=LLMModel.GEMINI_2_5_PRO, provider=LLMProvider.GOOGLE, default_context_window=1000000
        ),
        LLMModel.GEMINI_2_5_FLASH: LLM(
            model_name=LLMModel.GEMINI_2_5_FLASH, provider=LLMProvider.GOOGLE, default_context_window=1000000
        ),
        LLMModel.GEMINI_2_5_FLASH_LITE: LLM(
            model_name=LLMModel.GEMINI_2_5_FLASH_LITE, provider=LLMProvider.GOOGLE, default_context_window=128000
        ),
        # OpenAI
        LLMModel.GPT_5: LLM(model_name=LLMModel.GPT_5, provider=LLMProvider.OPENAI, default_context_window=400000),
        LLMModel.GPT_5_MINI: LLM(model_name=LLMModel.GPT_5_MINI, provider=LLMProvider.OPENAI,
                                 default_context_window=400000),
        LLMModel.GPT_5_NANO: LLM(model_name=LLMModel.GPT_5_NANO, provider=LLMProvider.OPENAI,
                                 default_context_window=400000),
        LLMModel.GPT_5_CHAT_LATEST: LLM(
            model_name=LLMModel.GPT_5_CHAT_LATEST, provider=LLMProvider.OPENAI, default_context_window=400000
        ),
        LLMModel.GPT_5_CODEX: LLM(
            model_name=LLMModel.GPT_5_CODEX, provider=LLMProvider.OPENAI, default_context_window=400000
        ),
        LLMModel.GPT_5_PRO: LLM(model_name=LLMModel.GPT_5_PRO, provider=LLMProvider.OPENAI,
                                default_context_window=400000),
        LLMModel.GPT_4_1: LLM(model_name=LLMModel.GPT_4_1, provider=LLMProvider.OPENAI, default_context_window=128000),
        LLMModel.GPT_4_1_MINI: LLM(
            model_name=LLMModel.GPT_4_1_MINI, provider=LLMProvider.OPENAI, default_context_window=128000
        ),
        LLMModel.GPT_4_1_NANO: LLM(
            model_name=LLMModel.GPT_4_1_NANO, provider=LLMProvider.OPENAI, default_context_window=128000
        ),
    }

    async def get_llm(self, model_name: LLMModel) -> LLM:
        """
        Retrieves an LLM instance from the registry.
        Raises KeyError if the model is not found.
        """
        return self._MODEL_REGISTRY[model_name]

    async def get_all_llms(self) -> list[LLM]:
        """Returns a list of all registered LLM instances."""
        return list(self._MODEL_REGISTRY.values())

    # todo: maybe cache by frontend session, passing session as arg as every session should be its own llm client?
    @alru_cache
    async def get_client(self, model_name: LLMModel, temperature: float, api_key: str) -> Union[OpenAI, Anthropic, GoogleGenAI]:
        """
        Retrieves an initialized LlamaIndex LLM client for the given model name.
        This method is cached to avoid re-creating clients with the same configuration.
        """
        llm_metadata = self._MODEL_REGISTRY.get(model_name)
        if not llm_metadata:
            raise KeyError(f"Model '{model_name}' not found in registry.")

        provider = llm_metadata.provider

        if provider == LLMProvider.OPENAI:
            return OpenAI(model=model_name, temperature=temperature, api_key=api_key)
        elif provider == LLMProvider.ANTHROPIC:
            return Anthropic(model=model_name, temperature=temperature, api_key=api_key)
        elif provider == LLMProvider.GOOGLE:
            return GoogleGenAI(model=model_name, temperature=temperature, api_key=api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
