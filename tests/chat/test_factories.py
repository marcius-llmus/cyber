from unittest.mock import AsyncMock

from app.chat.factories import build_chat_service, build_chat_turn_service
from app.chat.services import ChatService
from app.chat.services.turn import ChatTurnService
from app.chat.repositories import MessageRepository, ChatTurnRepository


class TestChatFactories:
    async def test_build_chat_service_returns_chat_service(self, mocker, db_session_mock):
        """build_chat_service returns a ChatService instance."""
        build_session_service_mock = mocker.patch(
            "app.chat.factories.build_session_service",
            new=AsyncMock(return_value=object()),
        )
        build_project_service_mock = mocker.patch(
            "app.chat.factories.build_project_service",
            new=AsyncMock(return_value=object()),
        )

        service = await build_chat_service(db=db_session_mock)
        assert isinstance(service, ChatService)
        build_session_service_mock.assert_awaited_once_with(db_session_mock)
        build_project_service_mock.assert_awaited_once_with(db_session_mock)

    async def test_build_chat_service_wires_message_repository_with_db(self, mocker, db_session_mock):
        """build_chat_service binds MessageRepository to the provided AsyncSession."""
        build_session_service_mock = mocker.patch(
            "app.chat.factories.build_session_service",
            new=AsyncMock(return_value=object()),
        )
        build_project_service_mock = mocker.patch(
            "app.chat.factories.build_project_service",
            new=AsyncMock(return_value=object()),
        )

        service = await build_chat_service(db=db_session_mock)
        assert isinstance(service.message_repo, MessageRepository)
        assert service.message_repo.db is db_session_mock
        build_session_service_mock.assert_awaited_once_with(db_session_mock)
        build_project_service_mock.assert_awaited_once_with(db_session_mock)

    async def test_build_chat_service_wires_session_service_and_project_service(self, mocker, db_session_mock):
        """build_chat_service awaits and wires SessionService + ProjectService."""
        expected_session_service = object()
        expected_project_service = object()

        build_session_service_mock = mocker.patch(
            "app.chat.factories.build_session_service",
            new=AsyncMock(return_value=expected_session_service),
        )
        build_project_service_mock = mocker.patch(
            "app.chat.factories.build_project_service",
            new=AsyncMock(return_value=expected_project_service),
        )

        service = await build_chat_service(db=db_session_mock)

        assert service.session_service is expected_session_service
        assert service.project_service is expected_project_service
        build_session_service_mock.assert_awaited_once_with(db_session_mock)
        build_project_service_mock.assert_awaited_once_with(db_session_mock)

    async def test_build_chat_turn_service_returns_chat_turn_service(self, db_session_mock):
        """build_chat_turn_service returns a ChatTurnService instance."""
        service = await build_chat_turn_service(db=db_session_mock)
        assert isinstance(service, ChatTurnService)

    async def test_build_chat_turn_service_wires_chat_turn_repository_with_db(self, db_session_mock):
        """build_chat_turn_service binds ChatTurnRepository to the provided AsyncSession."""
        service = await build_chat_turn_service(db=db_session_mock)
        assert isinstance(service.turn_repo, ChatTurnRepository)
        assert service.turn_repo.db is db_session_mock