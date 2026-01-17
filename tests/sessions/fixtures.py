from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import OperationalMode
from app.projects.models import Project
from app.sessions.dependencies import get_session_page_service, get_session_service
from app.sessions.models import ChatSession
from app.sessions.repositories import ChatSessionRepository
from app.sessions.services import SessionPageService, SessionService


@pytest.fixture
async def chat_session(db_session: AsyncSession, project: Project) -> ChatSession:
    session = ChatSession(
        name="Test Session",
        project_id=project.id,
        operational_mode=OperationalMode.CODING,
        is_active=False,
    )
    db_session.add(session)
    await db_session.flush()
    await db_session.refresh(session)
    return session


@pytest.fixture
def chat_session_repository(db_session: AsyncSession) -> ChatSessionRepository:
    return ChatSessionRepository(db=db_session)


@pytest.fixture
def chat_session_repository_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ChatSessionRepository, instance=True)


@pytest.fixture
def session_service(
    chat_session_repository_mock: MagicMock,
    project_service_mock: MagicMock,
) -> SessionService:
    """Provides a SessionService instance with MOCKED dependencies."""
    return SessionService(
        session_repo=chat_session_repository_mock,
        project_service=project_service_mock,
    )


@pytest.fixture
def session_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(SessionService, instance=True)


@pytest.fixture
def session_page_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(SessionPageService, instance=True)


@pytest.fixture
def override_get_session_service(client, session_service_mock: MagicMock):
    client.app.dependency_overrides[get_session_service] = lambda: session_service_mock
    yield
    client.app.dependency_overrides.clear()


@pytest.fixture
def override_get_session_page_service(client, session_page_service_mock: MagicMock):
    client.app.dependency_overrides[get_session_page_service] = (
        lambda: session_page_service_mock
    )
    yield
    client.app.dependency_overrides.clear()
