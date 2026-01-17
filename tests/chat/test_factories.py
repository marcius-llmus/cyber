from unittest.mock import AsyncMock

from app.chat.factories import build_chat_service, build_chat_turn_service
from app.chat.repositories import ChatTurnRepository, MessageRepository
from app.chat.services import ChatService
from app.chat.services.turn import ChatTurnService


class TestChatFactories:
    async def test_build_chat_service_returns_chat_service(
        self,
        mocker,
        db_session_mock,
        session_service_mock,
        project_service_mock,
    ):
        """build_chat_service returns a ChatService instance."""
        build_session_service_mock = mocker.patch(
            "app.chat.factories.build_session_service",
            new=AsyncMock(return_value=session_service_mock),
        )
        build_project_service_mock = mocker.patch(
            "app.chat.factories.build_project_service",
            new=AsyncMock(return_value=project_service_mock),
        )

        service = await build_chat_service(db=db_session_mock)
        assert isinstance(service, ChatService)
        build_session_service_mock.assert_awaited_once_with(db_session_mock)
        build_project_service_mock.assert_awaited_once_with(db_session_mock)

    async def test_build_chat_service_wires_message_repository_with_db(
        self,
        mocker,
        db_session_mock,
        session_service_mock,
        project_service_mock,
    ):
        """build_chat_service binds MessageRepository to the provided AsyncSession."""
        build_session_service_mock = mocker.patch(
            "app.chat.factories.build_session_service",
            new=AsyncMock(return_value=session_service_mock),
        )
        build_project_service_mock = mocker.patch(
            "app.chat.factories.build_project_service",
            new=AsyncMock(return_value=project_service_mock),
        )

        service = await build_chat_service(db=db_session_mock)
        assert isinstance(service.message_repo, MessageRepository)
        assert service.message_repo.db is db_session_mock
        build_session_service_mock.assert_awaited_once_with(db_session_mock)
        build_project_service_mock.assert_awaited_once_with(db_session_mock)

    async def test_build_chat_service_wires_session_service_and_project_service(
        self,
        mocker,
        db_session_mock,
        session_service_mock,
        project_service_mock,
    ):
        """build_chat_service awaits and wires SessionService + ProjectService."""
        build_session_service_mock = mocker.patch(
            "app.chat.factories.build_session_service",
            new=AsyncMock(return_value=session_service_mock),
        )
        build_project_service_mock = mocker.patch(
            "app.chat.factories.build_project_service",
            new=AsyncMock(return_value=project_service_mock),
        )

        service = await build_chat_service(db=db_session_mock)

        assert service.session_service is session_service_mock
        assert service.project_service is project_service_mock
        build_session_service_mock.assert_awaited_once_with(db_session_mock)
        build_project_service_mock.assert_awaited_once_with(db_session_mock)

    async def test_build_chat_turn_service_returns_chat_turn_service(
        self, db_session_mock
    ):
        """build_chat_turn_service returns a ChatTurnService instance."""
        service = await build_chat_turn_service(db=db_session_mock)
        assert isinstance(service, ChatTurnService)

    async def test_build_chat_turn_service_wires_chat_turn_repository_with_db(
        self, db_session_mock
    ):
        """build_chat_turn_service binds ChatTurnRepository to the provided AsyncSession."""
        service = await build_chat_turn_service(db=db_session_mock)
        assert isinstance(service.turn_repo, ChatTurnRepository)
        assert service.turn_repo.db is db_session_mock
