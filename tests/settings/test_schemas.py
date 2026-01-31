import pytest
from pydantic import ValidationError

from app.settings.schemas import LLMSettingsUpdate, SettingsUpdate


class TestSettingsSchemas:
    def test_llm_settings_update__accepts_reasoning_config_dict(self):
        """LLMSettingsUpdate should accept reasoning_config as an arbitrary dict payload."""
        obj = LLMSettingsUpdate(reasoning_config={"reasoning_effort": "high"})
        assert obj.reasoning_config == {"reasoning_effort": "high"}

    def test_settings_update__accepts_nested_coding_llm_settings_with_reasoning_config(
        self,
    ):
        """SettingsUpdate should parse nested coding_llm_settings.reasoning_config."""
        settings_in = SettingsUpdate(
            coding_llm_settings_id=123,
            coding_llm_settings=LLMSettingsUpdate(
                reasoning_config={"reasoning_effort": "high"}
            ),
        )

        assert settings_in.coding_llm_settings_id == 123
        assert settings_in.coding_llm_settings is not None
        assert settings_in.coding_llm_settings.reasoning_config == {
            "reasoning_effort": "high"
        }

    def test_settings_update__requires_coding_llm_settings_id_even_if_other_fields_present(
        self,
    ):
        """coding_llm_settings_id is a required field on SettingsUpdate.

        This ensures clients include it when posting nested coding_llm_settings updates.
        """
        with pytest.raises(ValidationError):
            SettingsUpdate(
                coding_llm_temperature="0.70",
                coding_llm_settings=LLMSettingsUpdate(
                    reasoning_config={"reasoning_effort": "high"}
                ),
            )
