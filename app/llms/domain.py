from dataclasses import dataclass

from app.llms.enums import LLMModel, LLMProvider


@dataclass(frozen=True)
class LLM:
    model_name: LLMModel
    provider: LLMProvider
    default_context_window: int
