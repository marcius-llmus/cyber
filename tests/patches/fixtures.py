from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.services import CodebaseService
from app.llms.services import LLMService
from app.patches.enums import PatchProcessorType
from app.patches.repositories import DiffPatchRepository
from app.patches.services import DiffPatchService
from app.patches.tools import PatcherTools
from app.projects.services import ProjectService


@pytest.fixture
def diff_patch_repository(db_session: AsyncSession) -> DiffPatchRepository:
    return DiffPatchRepository(db=db_session)


@pytest.fixture
def diff_patch_repository_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(DiffPatchRepository, instance=True)


@pytest.fixture
def diff_patch_repo_factory_mock(
    mocker: MockerFixture, diff_patch_repository_mock: MagicMock
) -> MagicMock:
    factory = mocker.MagicMock()
    factory.return_value = diff_patch_repository_mock
    return factory


@pytest.fixture
def diff_patch_service(
    db_sessionmanager_mock,
    diff_patch_repo_factory_mock: MagicMock,
) -> DiffPatchService:
    return DiffPatchService(
        db=db_sessionmanager_mock,
        diff_patch_repo_factory=diff_patch_repo_factory_mock,
        llm_service_factory=AsyncMock(),
        project_service_factory=AsyncMock(),
        codebase_service_factory=AsyncMock(),
    )


@pytest.fixture
def diff_patch_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(DiffPatchService, instance=True)


@pytest.fixture
def patcher_tools(mocker: MockerFixture, db_sessionmanager_mock, settings_snapshot):
    toolset = PatcherTools(
        db=db_sessionmanager_mock,
        settings_snapshot=settings_snapshot,
    )
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
def udiff_text_with_2_additions_1_deletion() -> str:
    return (
        "--- a/a.txt\n"
        "+++ b/a.txt\n"
        "@@ -1,1 +1,2 @@\n"
        "-bye\n"
        "+hello\n"
        "+world\n"
    )


@pytest.fixture
def codex_text_with_2_additions_1_deletion() -> str:
    return (
        "*** Begin Patch\n"
        "*** Update File: a.txt\n"
        "@@\n"
        "-bye\n"
        "+hello\n"
        "+world\n"
        "*** End Patch\n"
    )


@pytest.fixture
def diff_text_by_processor_type(
    udiff_text_with_2_additions_1_deletion: str,
    codex_text_with_2_additions_1_deletion: str,
) -> dict[PatchProcessorType, str]:
    return {
        PatchProcessorType.UDIFF_LLM: udiff_text_with_2_additions_1_deletion,
        PatchProcessorType.CODEX_APPLY: codex_text_with_2_additions_1_deletion,
    }
