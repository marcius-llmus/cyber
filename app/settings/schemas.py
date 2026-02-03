from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.core.enums import RepoMapMode
from app.llms.enums import LLMModel, LLMProvider
from app.patches.enums import PatchProcessorType
from app.settings.constants import API_KEY_MASK


class LLMSettingsBase(BaseModel):
    model_name: LLMModel
    context_window: int
    provider: LLMProvider
    visual_name: str
    reasoning_config: dict | None = None


class LLMSettingsCreate(LLMSettingsBase):
    pass


class LLMSettingsRead(LLMSettingsBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# schemas are part of the business logic. if exclude was removed from reasoning for example
# it would save an invalid data (see the save for provider logics)
class LLMSettingsUpdate(BaseModel):
    context_window: int | None = None
    # api_key and reasoning are updated for all providers. that's why we exclude (see service logic)
    api_key: str | None = Field(default=None, exclude=True)
    reasoning_config: dict[str, Any] | None = Field(default=None, exclude=True)

    @field_validator("api_key")  # noqa
    @classmethod
    def normalize_api_key(cls, value: str | None) -> str | None:
        """Setter behavior:

        - If the frontend sends the mask, treat it as "unset" (None) so repository update ignores it.
        - If the frontend sends any other value (including ""), pass it through.
          This allows users to clear the key by sending an empty string.
        """
        if value == API_KEY_MASK:
            return None
        return value


class LLMSettingsReadPublic(LLMSettingsRead):
    """Sanitized settings for rendering/pages.

    Notes:
        - api_key is always a computed display value (mask or empty string)
        - it is never the real provider api key
    """

    # Internal-only. Used to compute the display value.
    api_key_present: bool = Field(default=False, exclude=True)

    @computed_field  # type: ignore[misc]
    @property
    def api_key(self) -> str:
        """Computed getter for pages/templates.

        Never exposes the real provider API key.
        - If an API key exists for the provider: returns the mask
        - Otherwise: returns an empty string
        """

        return API_KEY_MASK if self.api_key_present else ""


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
