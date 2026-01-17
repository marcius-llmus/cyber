import inspect
from unittest.mock import AsyncMock

import pytest

from app.settings import dependencies
from app.settings.repositories import SettingsRepository
from app.settings.services import SettingsPageService


class TestSettingsDependencies:
    async def test_get_settings_repository_returns_repository(self, db_session_mock):
        repo = await dependencies.get_settings_repository(db=db_session_mock)
        assert isinstance(repo, SettingsRepository)
        assert repo.db is db_session_mock

    async def test_get_settings_service_is_async_dependency(self):
        assert inspect.iscoroutinefunction(dependencies.get_settings_service)

    async def test_get_settings_service_returns_service_instance(
        self,
        db_session_mock,
        mocker,
        settings_service_mock,
    ):
        build_settings_service_mock = mocker.patch(
            "app.settings.dependencies.build_settings_service",
            new=AsyncMock(return_value=settings_service_mock),
        )

        service = await dependencies.get_settings_service(db=db_session_mock)

        assert service is settings_service_mock
        build_settings_service_mock.assert_awaited_once_with(db_session_mock)

    async def test_get_settings_page_service_wires_settings_service_and_llm_service(
        self,
        db_session_mock,
        mocker,
        settings_service_mock,
        llm_service_mock,
    ):
        build_llm_service_mock = mocker.patch(
            "app.settings.dependencies.build_llm_service",
            new=AsyncMock(return_value=llm_service_mock),
        )

        page_service = await dependencies.get_settings_page_service(
            settings_service=settings_service_mock,
            db=db_session_mock,
        )

        assert isinstance(page_service, SettingsPageService)
        assert page_service.settings_service is settings_service_mock
        assert page_service.llm_service is llm_service_mock
        build_llm_service_mock.assert_awaited_once_with(db_session_mock)

    async def test_get_settings_service_propagates_factory_errors(self, db_session_mock, mocker):
        build_settings_service_mock = mocker.patch(
            "app.settings.dependencies.build_settings_service",
            new=AsyncMock(side_effect=ValueError("Boom")),
        )

        with pytest.raises(ValueError, match="Boom"):
            await dependencies.get_settings_service(db=db_session_mock)

        build_settings_service_mock.assert_awaited_once_with(db_session_mock)


    async def test_get_settings_page_service_propagates_factory_errors(
        self,
        db_session_mock,
        mocker,
        settings_service_mock,
    ):
        build_llm_service_mock = mocker.patch(
            "app.settings.dependencies.build_llm_service",
            new=AsyncMock(side_effect=ValueError("Boom")),
        )

        with pytest.raises(ValueError, match="Boom"):
            await dependencies.get_settings_page_service(
                settings_service=settings_service_mock,
                db=db_session_mock,
            )

        build_llm_service_mock.assert_awaited_once_with(db_session_mock)
