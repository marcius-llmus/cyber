from unittest.mock import AsyncMock

from app.llms.enums import LLMProvider
from app.settings.constants import API_KEY_MASK


class TestSettingsPageServiceApiKeyMasking:
    async def test_get_llm_dependent_fields_data_by_id__masks_api_key_when_present(
        self,
        settings_page_service,
        llm_settings_repository_mock,
        llm_settings,
        mocker,
    ):
        """Scenario: provider has an API key set.

        Asserts:
            - returned context uses masked placeholder, not the real key
            - provider is returned as provider.value
        """
        llm_settings = mocker.MagicMock()
        llm_settings.provider = LLMProvider.OPENAI

        llm_settings_repository_mock.get = AsyncMock(return_value=llm_settings)
        llm_settings_repository_mock.get_api_key_for_provider = AsyncMock(
            return_value="sk-real"
        )

        data = await settings_page_service.get_llm_dependent_fields_data_by_id(1)

        assert data["provider"] == "OPENAI"
        assert data["api_key"] == API_KEY_MASK

    async def test_get_llm_dependent_fields_data_by_id__returns_blank_when_missing(
        self,
        settings_page_service,
        llm_settings_repository_mock,
        llm_settings,
        mocker,
    ):
        """Scenario: provider has no API key set.

        Asserts:
            - returned context contains blank string
        """
        llm_settings = mocker.MagicMock()
        llm_settings.provider = LLMProvider.OPENAI

        llm_settings_repository_mock.get = AsyncMock(return_value=llm_settings)
        llm_settings_repository_mock.get_api_key_for_provider = AsyncMock(
            return_value=None
        )

        data = await settings_page_service.get_llm_dependent_fields_data_by_id(1)
        assert data["api_key"] == ""

    async def test_get_llm_dependent_fields_data_by_id__uses_shared_mask_constant(
        self,
        settings_page_service,
        llm_settings_repository_mock,
        mocker,
    ):
        llm_settings = mocker.MagicMock()
        llm_settings.provider = LLMProvider.OPENAI

        llm_settings_repository_mock.get = AsyncMock(return_value=llm_settings)
        llm_settings_repository_mock.get_api_key_for_provider = AsyncMock(
            return_value="sk-real"
        )

        data = await settings_page_service.get_llm_dependent_fields_data_by_id(1)
        assert data["api_key"] == API_KEY_MASK
