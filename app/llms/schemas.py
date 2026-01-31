from typing import Any, Literal

from pydantic import BaseModel, Field

from app.llms.enums import LLMModel, LLMProvider


class LLM(BaseModel):
    model_name: LLMModel
    provider: LLMProvider
    default_context_window: int = Field(gt=0)
    visual_name: str
    reasoning: dict[str, Any]


class OpenAIReasoningConfig(BaseModel):
    reasoning_effort: Literal["minimal", "low", "medium", "high"] = "medium"


class AnthropicReasoningConfig(BaseModel):
    type: Literal["enabled", "disabled"] = "enabled"
    budget_tokens: int = Field(ge=1, le=16000, default=8000)


class GoogleReasoningConfig(BaseModel):
    thinking_level: Literal["LOW", "HIGH", "MEDIUM", "MINIMAL"] = "LOW"
