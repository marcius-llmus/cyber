from enum import StrEnum


class LLMProvider(StrEnum):
    ANTHROPIC = "Anthropic"
    GOOGLE = "Google"
    OPENAI = "OpenAI"


class LLMModel(StrEnum):
    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5"
    CLAUDE_OPUS_4_1 = "claude-opus-4-1"
    GEMINI_3_PRO = "gemini-3-pro-preview"
    GEMINI_3_FLASH = "gemini-3-flash-preview"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    GPT_5 = "gpt-5-2025-08-07"
    GPT_5_MINI = "gpt-5-mini-2025-08-07"
    GPT_5_NANO = "gpt-5-nano-2025-04-14"
    GPT_5_CHAT_LATEST = "gpt-5-chat-latest"
    GPT_5_CODEX = "gpt-5-codex"
    GPT_5_PRO = "gpt-5-pro-2025-10-06"
    GPT_4_1 = "gpt-4.1-2025-04-14"
    GPT_4_1_MINI = "gpt-4.1-mini-2025-04-14"
    GPT_4_1_NANO = "gpt-4.1-nano-2025-04-14"


class LLMRole(StrEnum):
    CODER = "coder"
