from enum import StrEnum


class PatchStrategy(StrEnum):
    LLM_GATHER = "llm_gather"
    PROGRAMMATIC = "programmatic"
