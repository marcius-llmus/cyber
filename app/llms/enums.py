from enum import StrEnum


class LLMProvider(StrEnum):
    ANTHROPIC = "ANTHROPIC"
    GOOGLE = "GOOGLE"
    OPENAI = "OPENAI"


class LLMModel(StrEnum):
    # Anthropic
    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5"
    CLAUDE_OPUS_4_1 = "claude-opus-4-1"

    # Google
    GEMINI_3_PRO = "gemini-3-pro-preview"
    GEMINI_3_FLASH = "gemini-3-flash-preview"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"

    # Closed AI (lol)
    GPT_4 = "gpt-4"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_5 = "gpt-5-2025-08-07"
    GPT_5_MINI = "gpt-5-mini-2025-08-07"
    GPT_5_CHAT_LATEST = "gpt-5-chat-latest"
    GPT_5_PRO = "gpt-5-pro-2025-10-06"
    GPT_5_1 = "gpt-5.1-2025-11-13"
    GPT_5_1_CHAT_LATEST = "gpt-5.1-chat-latest"
    GPT_5_2 = "gpt-5.2-2025-12-11"
    O1 = "o1-2024-12-17"
    O1_PRO = "o1-pro-2025-03-19"
    O3 = "o3-2025-04-16"
    O3_MINI = "o3-mini-2025-01-31"
    O4_MINI = "o4-mini-2025-04-16"
    GPT_5_NANO = "gpt-5-nano-2025-04-14"
    GPT_4_1 = "gpt-4.1-2025-04-14"
    GPT_4_1_MINI = "gpt-4.1-mini-2025-04-14"
    GPT_4_1_NANO = "gpt-4.1-nano-2025-04-14"


class LLMRole(StrEnum):
    CODER = "CODER"
