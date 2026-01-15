from app.chat.factories import build_chat_service, build_chat_turn_service
from app.chat.services import ChatService
from app.chat.services.turn import ChatTurnService
from app.chat.repositories import MessageRepository, ChatTurnRepository


class TestChatFactories:
    async def test_build_chat_service_returns_chat_service(self, db_session):
        """build_chat_service returns a ChatService instance."""
        service = await build_chat_service(db=db_session)
        assert isinstance(service, ChatService)

    async def test_build_chat_service_wires_message_repository_with_db(self, db_session):
        """build_chat_service binds MessageRepository to the provided AsyncSession."""
        service = await build_chat_service(db=db_session)
        assert isinstance(service.message_repo, MessageRepository)
        assert service.message_repo.db is db_session

    async def test_build_chat_service_wires_session_service_and_project_service(self, db_session):
        """build_chat_service awaits and wires SessionService + ProjectService."""
        service = await build_chat_service(db=db_session)
        assert service.session_service is not None
        assert service.project_service is not None

    async def test_build_chat_turn_service_returns_chat_turn_service(self, db_session):
        """build_chat_turn_service returns a ChatTurnService instance."""
        service = await build_chat_turn_service(db=db_session)
        assert isinstance(service, ChatTurnService)

    async def test_build_chat_turn_service_wires_chat_turn_repository_with_db(self, db_session):
        """build_chat_turn_service binds ChatTurnRepository to the provided AsyncSession."""
        service = await build_chat_turn_service(db=db_session)
        assert isinstance(service.turn_repo, ChatTurnRepository)
        assert service.turn_repo.db is db_session