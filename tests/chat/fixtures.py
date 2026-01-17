from unittest.mock import MagicMock
import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.dependencies import get_chat_service, get_chat_turn_service
from app.chat.repositories import ChatTurnRepository, MessageRepository
from app.chat.services import ChatService
from app.chat.services.turn import ChatTurnService
from app.sessions.models import ChatSession


@pytest.fixture
def message_repository(db_session: AsyncSession) -> MessageRepository:
    return MessageRepository(db=db_session)


@pytest.fixture
def chat_turn_repository(db_session: AsyncSession) -> ChatTurnRepository:
    return ChatTurnRepository(db=db_session)


@pytest.fixture
def message_repository_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(MessageRepository, instance=True)


@pytest.fixture
def chat_turn_repository_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ChatTurnRepository, instance=True)


@pytest.fixture
def chat_service(
    message_repository_mock: MagicMock,
    session_service_mock: MagicMock,
    project_service_mock: MagicMock,
) -> ChatService:
    return ChatService(
        message_repo=message_repository_mock,
        session_service=session_service_mock,
        project_service=project_service_mock,
    )


@pytest.fixture
def chat_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ChatService, instance=True)


@pytest.fixture
def chat_turn_service(
    chat_turn_repository_mock: MagicMock,
) -> ChatTurnService:
    return ChatTurnService(turn_repo=chat_turn_repository_mock)


@pytest.fixture
def chat_turn_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ChatTurnService, instance=True)


@pytest.fixture
def override_get_chat_service(client, chat_service_mock: MagicMock):
    client.app.dependency_overrides[get_chat_service] = lambda: chat_service_mock
    yield
    client.app.dependency_overrides.clear()


@pytest.fixture
def override_get_chat_turn_service(client, chat_turn_service_mock: MagicMock):
    client.app.dependency_overrides[get_chat_turn_service] = lambda: chat_turn_service_mock
    yield
    client.app.dependency_overrides.clear()


@pytest.fixture
async def chat_session(db_session: AsyncSession, project) -> ChatSession:
    session = ChatSession(name="Test Session", project_id=project.id)
    db_session.add(session)
    await db_session.flush()
    await db_session.refresh(session)
    return session