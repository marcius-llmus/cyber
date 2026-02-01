from unittest.mock import AsyncMock

from app.settings.constants import API_KEY_MASK
from app.settings.schemas import LLMSettingsUpdate


async def test_llm_service__update_settings__does_not_overwrite_when_all_hashes_placeholder_sent(
    llm_settings_openai_no_role_mock,
    llm_service,
):
    llm_service.llm_settings_repo.get = AsyncMock(
        return_value=llm_settings_openai_no_role_mock
    )
    llm_service.llm_settings_repo.update = AsyncMock(
        return_value=llm_settings_openai_no_role_mock
    )
    llm_service.llm_settings_repo.update_api_key_for_provider = AsyncMock()

    await llm_service.update_settings(
        llm_settings_openai_no_role_mock.id,
        LLMSettingsUpdate(api_key=API_KEY_MASK),
    )

    llm_service.llm_settings_repo.update_api_key_for_provider.assert_not_awaited()


async def test_llm_service__update_settings__clears_api_key_when_empty_string_sent(
    llm_settings_openai_no_role_mock,
    llm_service,
):
    llm_service.llm_settings_repo.get = AsyncMock(
        return_value=llm_settings_openai_no_role_mock
    )
    llm_service.llm_settings_repo.update = AsyncMock(
        return_value=llm_settings_openai_no_role_mock
    )
    llm_service.llm_settings_repo.update_api_key_for_provider = AsyncMock()

    await llm_service.update_settings(
        llm_settings_openai_no_role_mock.id,
        LLMSettingsUpdate(api_key=""),
    )

    llm_service.llm_settings_repo.update_api_key_for_provider.assert_awaited_once_with(
        provider=llm_settings_openai_no_role_mock.provider,
        api_key="",
    )
