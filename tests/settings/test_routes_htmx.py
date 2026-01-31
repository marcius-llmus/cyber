from unittest.mock import AsyncMock

import pytest

from app.llms.exceptions import InvalidLLMReasoningConfigException
from app.settings.schemas import SettingsUpdate


class TestSettingsHtmxRoutes:
    @pytest.mark.usefixtures("override_get_settings_service")
    def test_update_settings__accepts_reasoning_config_payload_and_calls_settings_service(
        self,
        client,
        settings_service_mock,
    ):
        """POST /settings/ should accept coding_llm_settings.reasoning_config and delegate to SettingsService.

        Asserts:
            - HTTP 204
            - SettingsService.update_settings awaited once
            - SettingsUpdate passed to service includes nested reasoning_config
        """

        settings_service_mock.update_settings = AsyncMock()

        payload = {
            "coding_llm_temperature": "0.70",
            "coding_llm_settings_id": 123,
            "coding_llm_settings": {"reasoning_config": {"reasoning_effort": "high"}},
        }

        response = client.post(
            "/settings/",
            json=payload,
            headers={"HX-Request": "true"},
        )

        assert response.status_code == 204
        assert response.headers.get("HX-Trigger") == "settingsSaved"

        settings_service_mock.update_settings.assert_awaited_once()
        call_kwargs = settings_service_mock.update_settings.call_args.kwargs
        assert "settings_in" in call_kwargs
        assert isinstance(call_kwargs["settings_in"], SettingsUpdate)
        assert call_kwargs["settings_in"].coding_llm_settings is not None
        assert call_kwargs["settings_in"].coding_llm_settings.reasoning_config == {
            "reasoning_effort": "high"
        }

    @pytest.mark.usefixtures("override_get_settings_service")
    def test_update_settings__returns_400_when_invalid_llm_reasoning_config_exception(
        self,
        client,
        settings_service_mock,
    ):
        """POST /settings/ should return HTTP 400 when InvalidLLMReasoningConfigException is raised."""

        settings_service_mock.update_settings = AsyncMock(
            side_effect=InvalidLLMReasoningConfigException("Boom")
        )

        payload = {
            "coding_llm_temperature": "0.70",
            "coding_llm_settings_id": 123,
            "coding_llm_settings": {
                "reasoning_config": {"reasoning_effort": "INVALID"}
            },
        }

        response = client.post(
            "/settings/",
            json=payload,
            headers={"HX-Request": "true"},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Boom"
        settings_service_mock.update_settings.assert_awaited_once()
