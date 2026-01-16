from unittest.mock import MagicMock
import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.models import ContextFile
from app.context.repositories import ContextRepository
from app.context.services import WorkspaceService
from app.context.services.codebase import CodebaseService
from app.projects.services import ProjectService


@pytest.fixture
def context_repository(db_session: AsyncSession) -> ContextRepository:
    return ContextRepository(db=db_session)


@pytest.fixture
def context_repository_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ContextRepository, instance=True)


@pytest.fixture
async def context_file(db_session: AsyncSession, chat_session) -> ContextFile:
    context_file = ContextFile(
        session_id=chat_session.id, file_path="src/main.py", hit_count=1
    )
    db_session.add(context_file)
    await db_session.flush()
    await db_session.refresh(context_file)
    return context_file


@pytest.fixture
def codebase_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(CodebaseService, instance=True)


@pytest.fixture
def project_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ProjectService, instance=True)


@pytest.fixture
def workspace_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(WorkspaceService, instance=True)


@pytest.fixture
def chat_session_mock(mocker: MockerFixture) -> MagicMock:
    """Unit-test safe ChatSession stand-in (no DB)."""
    obj = mocker.MagicMock()
    obj.id = 1
    return obj