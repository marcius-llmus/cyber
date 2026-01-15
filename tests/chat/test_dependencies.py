"""Dependency tests for the chat app.

Skeleton-only: implement assertions later.
"""

import inspect


class TestChatDependencies:
    async def test_get_message_repository_returns_repository_instance(self):
        """get_message_repository returns a MessageRepository bound to the request db session."""
        pass

    async def test_get_chat_service_is_async_dependency(self):
        """get_chat_service remains an async dependency (coroutine function)."""
        pass

    async def test_get_chat_turn_service_is_async_dependency(self):
        """get_chat_turn_service remains an async dependency (coroutine function)."""
        pass

    async def test_get_chat_service_wires_message_repo_session_service_project_service(self):
        """get_chat_service returns ChatService wired with MessageRepository + SessionService + ProjectService."""
        pass

    async def test_get_chat_turn_service_wires_chat_turn_repository(self):
        """get_chat_turn_service returns ChatTurnService wired with ChatTurnRepository."""
        pass

    async def test_get_chat_service_propagates_factory_errors(self):
        """get_chat_service surfaces exceptions raised by build_chat_service."""
        pass

    async def test_get_chat_turn_service_propagates_factory_errors(self):
        """get_chat_turn_service surfaces exceptions raised by build_chat_turn_service."""
        pass

    async def test_get_message_repository_is_async_dependency(self):
        """get_message_repository remains an async dependency (coroutine function)."""
        pass

    async def test_dependencies_are_declared_async(self):
        """All chat dependencies should be declared async for consistency with other apps."""
        pass