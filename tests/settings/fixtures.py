from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.llms.registry import LLMFactory
from app.settings.dependencies import get_settings_service
from app.settings.models import Settings
from app.settings.repositories import SettingsRepository
from app.settings.services import SettingsPageService, SettingsService


@pytest.fixture
async def settings(db_session: AsyncSession) -> Settings:
    """Creates a default singleton Settings record."""
    db_obj = Settings(
        id=1,
        max_history_length=50,
        ast_token_limit=10_000,
        grep_token_limit=4_000,
        diff_patches_auto_open=True,
        diff_patches_auto_apply=True,
        coding_llm_temperature=Decimal("0.7"),
    )
    db_session.add(db_obj)
    await db_session.flush()
    await db_session.refresh(db_obj)
    return db_obj


@pytest.fixture
def settings_repository(db_session: AsyncSession) -> SettingsRepository:
    return SettingsRepository(db=db_session)


@pytest.fixture
def settings_repository_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(SettingsRepository, instance=True)


@pytest.fixture
def settings_service(
    settings_repository_mock: MagicMock, llm_service_mock: MagicMock
) -> SettingsService:
    """Provides a real SettingsService with mocked dependencies for unit testing."""
    return SettingsService(settings_repo=settings_repository_mock, llm_service=llm_service_mock)


@pytest.fixture
def settings_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(SettingsService, instance=True)


@pytest.fixture
def settings_page_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(SettingsPageService, instance=True)


@pytest.fixture
def llm_factory_instance_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(LLMFactory, instance=True)


@pytest.fixture
def override_get_settings_service(client, settings_service_mock: MagicMock):
    client.app.dependency_overrides[get_settings_service] = lambda: settings_service_mock
    yield
    client.app.dependency_overrides.clear()
