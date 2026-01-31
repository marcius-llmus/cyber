from app.llms.enums import LLMModel, LLMProvider
from app.llms.schemas import LLM


class LLMFactory:
    _MODEL_REGISTRY: dict[LLMModel, LLM] = {
        # Anthropic
        LLMModel.CLAUDE_SONNET_4_5: LLM(
            model_name=LLMModel.CLAUDE_SONNET_4_5,
            provider=LLMProvider.ANTHROPIC,
            default_context_window=200000,
        ),
        LLMModel.CLAUDE_OPUS_4_5: LLM(
            model_name=LLMModel.CLAUDE_OPUS_4_5,
            provider=LLMProvider.ANTHROPIC,
            default_context_window=200000,
        ),
        # Google
        LLMModel.GEMINI_3_PRO: LLM(
            model_name=LLMModel.GEMINI_3_PRO,
            provider=LLMProvider.GOOGLE,
            default_context_window=1000000,
        ),
        LLMModel.GEMINI_3_FLASH: LLM(
            model_name=LLMModel.GEMINI_3_FLASH,
            provider=LLMProvider.GOOGLE,
            default_context_window=1000000,
        ),
        LLMModel.GEMINI_2_5_PRO: LLM(
            model_name=LLMModel.GEMINI_2_5_PRO,
            provider=LLMProvider.GOOGLE,
            default_context_window=1000000,
        ),
        LLMModel.GEMINI_2_5_FLASH: LLM(
            model_name=LLMModel.GEMINI_2_5_FLASH,
            provider=LLMProvider.GOOGLE,
            default_context_window=1000000,
        ),
        LLMModel.GEMINI_2_5_FLASH_LITE: LLM(
            model_name=LLMModel.GEMINI_2_5_FLASH_LITE,
            provider=LLMProvider.GOOGLE,
            default_context_window=128000,
        ),
        # OpenAI
        LLMModel.GPT_5_MINI: LLM(
            model_name=LLMModel.GPT_5_MINI,
            provider=LLMProvider.OPENAI,
            default_context_window=256000,
        ),
        LLMModel.GPT_5_2: LLM(
            model_name=LLMModel.GPT_5_2,
            provider=LLMProvider.OPENAI,
            default_context_window=256000,
        ),
        LLMModel.GPT_5_NANO: LLM(
            model_name=LLMModel.GPT_5_NANO,
            provider=LLMProvider.OPENAI,
            default_context_window=256000,
        ),
        LLMModel.GPT_4_1: LLM(
            model_name=LLMModel.GPT_4_1,
            provider=LLMProvider.OPENAI,
            default_context_window=256000,
        ),
        LLMModel.GPT_4_1_MINI: LLM(
            model_name=LLMModel.GPT_4_1_MINI,
            provider=LLMProvider.OPENAI,
            default_context_window=256000,
        ),
        LLMModel.GPT_4_1_NANO: LLM(
            model_name=LLMModel.GPT_4_1_NANO,
            provider=LLMProvider.OPENAI,
            default_context_window=256000,
        ),
    }

    async def get_llm(self, model_name: LLMModel) -> LLM:
        return self._MODEL_REGISTRY[model_name]

    async def get_all_llms(self) -> list[LLM]:
        return list(self._MODEL_REGISTRY.values())
