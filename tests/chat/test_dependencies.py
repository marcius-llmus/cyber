import pytest
from unittest.mock import AsyncMock, patch
import inspect
from app.chat.dependencies import (
    get_message_repository,
    get_chat_service,
    get_chat_turn_service,
)
from app.chat.repositories import MessageRepository, ChatTurnRepository
from app.chat.services.turn import ChatTurnService


class TestChatDependencies:
    async def test_get_message_repository_returns_repository_instance(self, db_session_mock):
        """get_message_repository returns a MessageRepository bound to the request db session."""
        repo = await get_message_repository(db=db_session_mock)
        assert isinstance(repo, MessageRepository)
        assert repo.db is db_session_mock

    async def test_get_chat_service_is_async_dependency(self):
        """get_chat_service remains an async dependency (coroutine function)."""
        assert inspect.iscoroutinefunction(get_chat_service)

    async def test_get_chat_turn_service_is_async_dependency(self):
        """get_chat_turn_service remains an async dependency (coroutine function)."""
        assert inspect.iscoroutinefunction(get_chat_turn_service)

    async def test_get_chat_service_wires_message_repo_session_service_project_service(self, db_session_mock, chat_service_mock):
        """get_chat_service delegates to build_chat_service and returns its result."""
        with patch(
            "app.chat.dependencies.build_chat_service",
            new=AsyncMock(return_value=chat_service_mock),
        ) as build_chat_service_mock:
            service = await get_chat_service(db=db_session_mock)

        assert service is chat_service_mock
        build_chat_service_mock.assert_awaited_once_with(db_session_mock)

    async def test_get_chat_turn_service_wires_chat_turn_repository(self, db_session_mock):
        """get_chat_turn_service returns ChatTurnService wired with ChatTurnRepository."""
        service = await get_chat_turn_service(db=db_session_mock)
        assert isinstance(service, ChatTurnService)
        assert isinstance(service.turn_repo, ChatTurnRepository)

    async def test_get_chat_service_propagates_factory_errors(self, db_session_mock):
        """get_chat_service surfaces exceptions raised by build_chat_service."""
        with patch(
            "app.chat.dependencies.build_chat_service",
            new=AsyncMock(side_effect=ValueError("Factory error")),
        ):
            with pytest.raises(ValueError, match="Factory error"):
                await get_chat_service(db=db_session_mock)

    async def test_get_chat_turn_service_propagates_factory_errors(self, db_session_mock):
        """get_chat_turn_service surfaces exceptions raised by build_chat_turn_service."""
        with patch(
            "app.chat.dependencies.build_chat_turn_service",
            new=AsyncMock(side_effect=ValueError("Factory error")),
        ):
            with pytest.raises(ValueError, match="Factory error"):
                await get_chat_turn_service(db=db_session_mock)

    async def test_get_message_repository_is_async_dependency(self):
        """get_message_repository remains an async dependency (coroutine function)."""
        assert inspect.iscoroutinefunction(get_message_repository)

    async def test_dependencies_are_declared_async(self):
        """All chat dependencies should be declared async for consistency with other apps."""
        assert inspect.iscoroutinefunction(get_message_repository)
        assert inspect.iscoroutinefunction(get_chat_service)
        assert inspect.iscoroutinefunction(get_chat_turn_service)