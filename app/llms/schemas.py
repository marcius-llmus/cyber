from typing import Any, Literal

from google.genai.types import ThinkingLevel
from pydantic import BaseModel, Field

from app.llms.enums import LLMModel, LLMProvider


class LLM(BaseModel):
    model_name: LLMModel
    provider: LLMProvider
    default_context_window: int = Field(gt=0)
    visual_name: str
    reasoning: dict[str, Any]


class OpenAIReasoningConfig(BaseModel):
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh"] = "medium"


class AnthropicReasoningConfig(BaseModel):
    type: Literal["enabled", "disabled"] = "enabled"
    budget_tokens: int = Field(ge=1, le=16000, default=8000)


class GoogleReasoningConfig(BaseModel):
    thinking_level: ThinkingLevel = Field(
        default=ThinkingLevel.MEDIUM,
        description="Optional. The number of thoughts tokens that the model should generate.",
    )
