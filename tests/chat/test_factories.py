"""Factory tests for the chat app.

Skeleton-only: implement assertions later.
"""


class TestChatFactories:
    async def test_build_chat_service_returns_chat_service(self):
        """build_chat_service returns a ChatService instance."""
        pass

    async def test_build_chat_service_wires_message_repository_with_db(self):
        """build_chat_service binds MessageRepository to the provided AsyncSession."""
        pass

    async def test_build_chat_service_wires_session_service_and_project_service(self):
        """build_chat_service awaits and wires SessionService + ProjectService."""
        pass

    async def test_build_chat_turn_service_returns_chat_turn_service(self):
        """build_chat_turn_service returns a ChatTurnService instance."""
        pass

    async def test_build_chat_turn_service_wires_chat_turn_repository_with_db(self):
        """build_chat_turn_service binds ChatTurnRepository to the provided AsyncSession."""
        pass