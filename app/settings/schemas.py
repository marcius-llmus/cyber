from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.llms.enums import LLMModel, LLMProvider
from app.settings.enums import CodingMode, ContextStrategy, OperationalMode


class LLMSettingsBase(BaseModel):
    model_name: LLMModel
    context_window: int
    provider: LLMProvider
    api_key: str | None = None


class LLMSettingsCreate(LLMSettingsBase):
    pass


class LLMSettingsRead(LLMSettingsBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class LLMSettingsUpdate(BaseModel):
    context_window: int | None = None
    api_key: str | None = None


class SettingsBase(BaseModel):
    operational_mode: OperationalMode
    coding_mode: CodingMode
    context_strategy: ContextStrategy
    max_history_length: int
    ast_token_limit: int
    grep_token_limit: int
    coding_llm_temperature: Decimal = Field(..., ge=0, le=1, max_digits=3, decimal_places=2)


class SettingsCreate(SettingsBase):
    pass


class SettingsUpdate(BaseModel):
    max_history_length: int | None = None
    ast_token_limit: int | None = None
    grep_token_limit: int | None = None
    coding_llm_temperature: Decimal | None = Field(default=None, ge=0, le=1, max_digits=3, decimal_places=2)
    coding_llm_settings_id: int = Field(exclude=True) # Exclude from Settings DB update
    coding_llm_settings: LLMSettingsUpdate | None = Field(default=None, exclude=True)
