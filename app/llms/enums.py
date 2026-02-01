from enum import StrEnum


class LLMProvider(StrEnum):
    ANTHROPIC = "ANTHROPIC"
    GOOGLE = "GOOGLE"
    OPENAI = "OPENAI"


class LLMModel(StrEnum):
    # Anthropic
    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5-20250929"
    CLAUDE_OPUS_4_5 = "claude-opus-4-5-20251101"
    CLAUDE_HAIKU_4_5 = "claude-haiku-4-5-20251001"

    # Google
    GEMINI_3_PRO = "gemini-3-pro-preview"
    GEMINI_3_FLASH = "gemini-3-flash-preview"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"

    # Closed AI (lol)
    GPT_5_2_CODEX = "gpt-5.2-codex"
    GPT_5_2 = "gpt-5.2-2025-12-11"
    GPT_5_MINI = "gpt-5-mini-2025-08-07"
    GPT_5_NANO = "gpt-5-nano-2025-04-14"
    GPT_4_1 = "gpt-4.1-2025-04-14"
    GPT_4_1_MINI = "gpt-4.1-mini-2025-04-14"
    GPT_4_1_NANO = "gpt-4.1-nano-2025-04-14"


class LLMRole(StrEnum):
    CODER = "CODER"
