from decimal import Decimal

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import RepoMapMode
from app.llms.enums import LLMModel, LLMProvider
from app.patches.enums import PatchProcessorType


class LLMSettingsBase(BaseModel):
    model_name: LLMModel
    context_window: int
    provider: LLMProvider
    visual_name: str
    api_key: str | None = None
    reasoning_config: dict | None = None


class LLMSettingsCreate(LLMSettingsBase):
    pass


class LLMSettingsRead(LLMSettingsBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class LLMSettingsUpdate(BaseModel):
    context_window: int | None = None
    api_key: str | None = None

    # Helper fields for reasoning config construction
    reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = Field(
        default=None, exclude=True
    )
    thinking_level: Literal["LOW", "HIGH", "MEDIUM", "MINIMAL"] | None = Field(
        default=None, exclude=True
    )
    budget_tokens: int | None = Field(default=None, exclude=True)

    reasoning_config: dict[str, Any] | None = None

    @model_validator(mode="after")
    def construct_reasoning_config(self) -> "LLMSettingsUpdate":
        if self.reasoning_config is not None:
            return self

        config = {}
        if self.reasoning_effort is not None:
            config["reasoning_effort"] = self.reasoning_effort

        if self.thinking_level is not None:
            config["thinking_level"] = self.thinking_level

        if self.budget_tokens is not None:
            config["budget_tokens"] = self.budget_tokens
            config["type"] = "enabled"

        if config:
            self.reasoning_config = config

        return self


class SettingsBase(BaseModel):
    max_history_length: int
    ast_token_limit: int
    grep_token_limit: int
    diff_patches_auto_open: bool
    diff_patches_auto_apply: bool
    diff_patch_processor_type: PatchProcessorType
    repomap_mode: RepoMapMode
    repomap_ignore_patterns: str | None = None
    coding_llm_temperature: Decimal = Field(
        ..., ge=0, le=1, max_digits=3, decimal_places=2
    )


class SettingsCreate(SettingsBase):
    pass


class SettingsUpdate(BaseModel):
    max_history_length: int | None = None
    ast_token_limit: int | None = None
    grep_token_limit: int | None = None
    diff_patches_auto_open: bool | None = None
    diff_patches_auto_apply: bool | None = None
    diff_patch_processor_type: PatchProcessorType | None = None
    repomap_mode: RepoMapMode | None = None
    repomap_ignore_patterns: str | None = None
    coding_llm_temperature: Decimal | None = Field(
        default=None, ge=0, le=1, max_digits=3, decimal_places=2
    )
    coding_llm_settings_id: int = Field(exclude=True)  # Exclude from Settings DB update
    coding_llm_settings: LLMSettingsUpdate | None = Field(default=None, exclude=True)


class AgentSettingsSnapshot(SettingsBase):
    model_config = ConfigDict(from_attributes=True)
