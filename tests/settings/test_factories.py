"""Factory tests for the settings app."""

from unittest.mock import AsyncMock

import pytest

from app.settings.factories import build_settings_service
from app.settings.services import SettingsService


class TestSettingsFactories:
    async def test_build_settings_service_returns_settings_service(
        self,
        db_session_mock,
        mocker,
        llm_service_mock,
    ):
        build_llm_service_mock = mocker.patch(
            "app.settings.factories.build_llm_service",
            new=AsyncMock(return_value=llm_service_mock),
        )

        service = await build_settings_service(db=db_session_mock)

        assert isinstance(service, SettingsService)
        assert service.settings_repo.db is db_session_mock
        assert service.llm_service is llm_service_mock
        build_llm_service_mock.assert_awaited_once_with(db_session_mock)

    async def test_build_settings_service_propagates_factory_errors(
        self,
        db_session_mock,
        mocker,
    ):
        build_llm_service_mock = mocker.patch(
            "app.settings.factories.build_llm_service",
            new=AsyncMock(side_effect=ValueError("Boom")),
        )

        with pytest.raises(ValueError, match="Boom"):
            await build_settings_service(db=db_session_mock)

        build_llm_service_mock.assert_awaited_once_with(db_session_mock)
