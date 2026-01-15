"""Service tests for the sessions app."""

import pytest
from unittest.mock import AsyncMock, MagicMock, call
from app.core.enums import OperationalMode
from app.sessions.services import SessionService, SessionPageService
from app.sessions.exceptions import ChatSessionNotFoundException
from app.projects.exceptions import ActiveProjectRequiredException
from app.sessions.schemas import ChatSessionCreate


async def test_set_active_session_orchestration(
    session_service: SessionService,
    chat_session_repository_mock: MagicMock,
    project_service_mock: MagicMock,
):
    """Verify it calls project.set_active -> repo.deactivate_all -> repo.activate -> project.set_active."""
    session_id = 123
    mock_session = MagicMock(id=session_id, project_id=456)
    chat_session_repository_mock.get_with_messages.return_value = mock_session
    chat_session_repository_mock.activate.return_value = mock_session

    result = await session_service.set_active_session(session_id)

    assert result is mock_session

    chat_session_repository_mock.get_with_messages.assert_awaited_once_with(session_id=session_id)
    chat_session_repository_mock.deactivate_all_for_project.assert_awaited_once_with(project_id=456)
    chat_session_repository_mock.activate.assert_awaited_once_with(mock_session)

    assert project_service_mock.set_active_project.call_args_list == [call(456), call(project_id=456)]


async def test_set_active_session_raises_when_session_not_found(
    session_service: SessionService,
    chat_session_repository_mock: MagicMock,
):
    """Verify set_active_session raises when session does not exist."""
    chat_session_repository_mock.get_with_messages.return_value = None

    with pytest.raises(ChatSessionNotFoundException, match="Session with id 999 not found"):
        await session_service.set_active_session(999)


async def test_delete_session_checks_active_project(session_service: SessionService, project_service_mock: MagicMock):
    """Verify error if no active project."""
    # Setup
    # Mock project_repo.get_active() to return None
    project_repo_mock = MagicMock()
    project_repo_mock.get_active = AsyncMock(return_value=None)
    project_service_mock.project_repo = project_repo_mock

    # Execute & Verify
    with pytest.raises(ActiveProjectRequiredException):
        await session_service.delete_session(123)


async def test_delete_session_returns_active_status(session_service: SessionService, chat_session_repository_mock: MagicMock, project_service_mock: MagicMock):
    """Verify return value indicates if deleted session was active."""
    # Setup
    project_repo_mock = MagicMock()
    project_repo_mock.get_active = AsyncMock(return_value=MagicMock(id=1))
    project_service_mock.project_repo = project_repo_mock

    # Case 1: Session was active
    active_session = MagicMock(is_active=True)
    chat_session_repository_mock.get.return_value = active_session

    was_active = await session_service.delete_session(123)
    assert was_active is True
    chat_session_repository_mock.get.assert_awaited_with(pk=123)
    chat_session_repository_mock.delete.assert_awaited_with(pk=123)

    # Case 2: Session was inactive
    inactive_session = MagicMock(is_active=False)
    chat_session_repository_mock.get.return_value = inactive_session

    was_active = await session_service.delete_session(456)
    assert was_active is False
    chat_session_repository_mock.get.assert_awaited_with(pk=456)
    chat_session_repository_mock.delete.assert_awaited_with(pk=456)


async def test_rename_session(session_service: SessionService, chat_session_repository_mock: MagicMock):
    """Verify validation (no empty names) and update."""
    # Test empty name
    with pytest.raises(ValueError, match="Session name cannot be empty"):
        await session_service.rename_session(123, "   ")

    # Test valid name
    mock_session = MagicMock()
    chat_session_repository_mock.get_with_messages.return_value = mock_session

    await session_service.rename_session(123, " New Name ")

    # Verify trim and update
    chat_session_repository_mock.update.assert_awaited_once()
    call_args = chat_session_repository_mock.update.call_args
    assert call_args.kwargs['obj_in'].name == "New Name"


async def test_get_operational_mode(session_service: SessionService, chat_session_repository_mock: MagicMock):
    """Verify getter."""
    mock_session = MagicMock(operational_mode=OperationalMode.CODING)
    chat_session_repository_mock.get_with_messages.return_value = mock_session

    mode = await session_service.get_operational_mode(123)
    assert mode == OperationalMode.CODING


async def test_set_operational_mode(session_service: SessionService, chat_session_repository_mock: MagicMock):
    """Verify setter."""
    mock_session = MagicMock()
    chat_session_repository_mock.get_with_messages.return_value = mock_session

    await session_service.set_operational_mode(123, OperationalMode.CHAT)

    chat_session_repository_mock.update.assert_awaited_once()
    call_args = chat_session_repository_mock.update.call_args
    assert call_args.kwargs['obj_in'].operational_mode == OperationalMode.CHAT


async def test_session_page_service_logic(session_service_mock: MagicMock, project_service_mock: MagicMock):
    """Verify SessionPageService logic."""
    page_service = SessionPageService(session_service=session_service_mock, project_service=project_service_mock)

    # Case 1: No active project
    project_repo_mock = MagicMock()
    project_repo_mock.get_active = AsyncMock(return_value=None)
    project_service_mock.project_repo = project_repo_mock

    data = await page_service.get_sessions_page_data()
    assert data == {"sessions": []}

    # Case 2: Active project
    mock_project = MagicMock(id=99)
    project_repo_mock.get_active = AsyncMock(return_value=mock_project)
    session_service_mock.get_sessions_by_project = AsyncMock(return_value=["s1", "s2"])

    data = await page_service.get_sessions_page_data()
    assert data["sessions"] == ["s1", "s2"]
    session_service_mock.get_sessions_by_project.assert_awaited_once_with(project_id=99)


async def test_create_session(session_service: SessionService, chat_session_repository_mock: MagicMock):
    """Verify create delegates to repo."""
    session_in = ChatSessionCreate(name="Test", project_id=1)
    await session_service.create_session(session_in)
    chat_session_repository_mock.create.assert_awaited_once_with(obj_in=session_in)


async def test_get_sessions_by_project(session_service: SessionService, chat_session_repository_mock: MagicMock):
    """Verify list delegates to repo."""
    await session_service.get_sessions_by_project(1)
    chat_session_repository_mock.list_by_project.assert_awaited_once_with(project_id=1)


async def test_get_most_recent_session_by_project(session_service: SessionService, chat_session_repository_mock: MagicMock):
    """Verify delegates to repo."""
    await session_service.get_most_recent_session_by_project(1)
    chat_session_repository_mock.get_most_recent_by_project.assert_awaited_once_with(project_id=1)


async def test_get_session_not_found(session_service: SessionService, chat_session_repository_mock: MagicMock):
    """Verify raises exception if not found."""
    chat_session_repository_mock.get_with_messages.return_value = None
    with pytest.raises(ChatSessionNotFoundException):
        await session_service.get_session(999)


async def test_get_session_returns_session(
    session_service: SessionService,
    chat_session_repository_mock: MagicMock,
):
    """Verify get_session returns the session when found."""
    mock_session = MagicMock(id=123)
    chat_session_repository_mock.get_with_messages.return_value = mock_session

    result = await session_service.get_session(123)

    assert result is mock_session
    chat_session_repository_mock.get_with_messages.assert_awaited_once_with(session_id=123)


async def test_delete_session_not_found(session_service: SessionService, chat_session_repository_mock: MagicMock, project_service_mock: MagicMock):
    """Verify delete raises exception if session not found."""
    project_repo_mock = MagicMock()
    project_repo_mock.get_active = AsyncMock(return_value=MagicMock(id=1))
    project_service_mock.project_repo = project_repo_mock

    chat_session_repository_mock.get.return_value = None

    with pytest.raises(ChatSessionNotFoundException):
        await session_service.delete_session(999)