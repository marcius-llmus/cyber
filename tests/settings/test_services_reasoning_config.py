from unittest.mock import AsyncMock

from app.settings.schemas import LLMSettingsUpdate, SettingsUpdate


class TestSettingsServiceReasoningConfig:
    async def test_settings_service__update_settings__delegates_coding_llm_settings_update_to_llm_service_update_coding_llm(
        self,
        settings_service,
        settings_repository_mock,
        llm_service_mock,
        settings,
    ):
        """Scenario: SettingsUpdate includes coding_llm_settings and coding_llm_settings_id.

        Asserts:
            - SettingsService calls llm_service.update_coding_llm with the provided id
            - passes through nested LLMSettingsUpdate including reasoning_config
            - updates the singleton Settings row via settings_repo.update
        """
        settings_repository_mock.get = AsyncMock(return_value=settings)
        settings_repository_mock.update = AsyncMock(return_value=settings)
        llm_service_mock.update_coding_llm = AsyncMock()

        settings_in = SettingsUpdate(
            coding_llm_temperature=settings.coding_llm_temperature,
            coding_llm_settings_id=123,
            coding_llm_settings=LLMSettingsUpdate(
                reasoning_config={"reasoning_effort": "high"}
            ),
        )

        await settings_service.update_settings(settings_in=settings_in)

        llm_service_mock.update_coding_llm.assert_awaited_once_with(
            llm_id=123,
            settings_in=settings_in.coding_llm_settings,
        )
        settings_repository_mock.update.assert_awaited_once()
