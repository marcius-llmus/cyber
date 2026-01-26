from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import DatabaseSessionManager
from app.settings.models import Settings
from app.context.services import CodebaseService
from app.llms.services import LLMService
from app.patches.dependencies import get_diff_patch_service
from app.patches.repositories import DiffPatchRepository
from app.patches.services import DiffPatchService
from app.projects.services import ProjectService


@pytest.fixture
def diff_patch_repository(db_session: AsyncSession) -> DiffPatchRepository:
    return DiffPatchRepository(db=db_session)


@pytest.fixture
def diff_patch_repository_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(DiffPatchRepository, instance=True)


@pytest.fixture
def diff_patch_service(
    diff_patch_repository_mock: MagicMock,
) -> DiffPatchService:
    return DiffPatchService(
        db=MagicMock(),
        diff_patch_repo_factory=lambda _db: diff_patch_repository_mock,
        llm_service_factory=AsyncMock(),
        project_service_factory=AsyncMock(),
        codebase_service_factory=AsyncMock(),
    )


@pytest.fixture
def diff_patch_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(DiffPatchService, instance=True)


@pytest.fixture
def settings_mock() -> Settings:
    return Settings()


@pytest.fixture
def sessionmanager_mock(mocker: MockerFixture) -> DatabaseSessionManager:
    return mocker.create_autospec(DatabaseSessionManager, instance=True)


@pytest.fixture
def patcher_tools(mocker: MockerFixture, sessionmanager_mock, settings_mock):
    from app.patches.tools import PatcherTools

    toolset = PatcherTools(db=sessionmanager_mock, settings=settings_mock)
    toolset.session_id = 123
    toolset.turn_id = "turn_123"
    return toolset


@pytest.fixture
def llm_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(LLMService, instance=True)


@pytest.fixture
def llm_client_mock(mocker: MockerFixture):
    return mocker.MagicMock()


@pytest.fixture
def project_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ProjectService, instance=True)


@pytest.fixture
def codebase_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(CodebaseService, instance=True)


@pytest.fixture
def file_read_result_success(mocker: MockerFixture):
    r = mocker.MagicMock()
    r.status = "SUCCESS"
    r.content = "original"
    r.error_message = None
    return r


@pytest.fixture
def override_get_diff_patch_service(client, diff_patch_service_mock: MagicMock):
    client.app.dependency_overrides[get_diff_patch_service] = (
        lambda: diff_patch_service_mock
    )
    yield
    client.app.dependency_overrides.pop(get_diff_patch_service, None)