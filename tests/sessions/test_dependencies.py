import pytest
from fastapi import Depends
from unittest.mock import MagicMock

from app.sessions.dependencies import get_session_repository, get_session_service, get_session_page_service
from app.sessions.repositories import ChatSessionRepository
from app.sessions.services import SessionService, SessionPageService


async def test_get_session_repository_returns_repo(mocker):
    """Verify dependency returns ChatSessionRepository."""
    db_mock = mocker.AsyncMock()
    repo = await get_session_repository(db=db_mock)
    assert isinstance(repo, ChatSessionRepository)
    assert repo.db is db_mock


async def test_get_session_service_returns_service(mocker, project_service_mock: MagicMock):
    """Verify dependency returns SessionService."""
    db_mock = mocker.Mock()
    
    # Mock the factory call to avoid executing factory logic (tested separately)
    # and to avoid needing real DB interactions.
    mock_service = mocker.Mock(spec=SessionService)
    mocker.patch("app.sessions.dependencies.build_session_service", new_callable=mocker.AsyncMock, return_value=mock_service)
    
    service = await get_session_service(db=db_mock)
    
    assert service is mock_service


async def test_get_session_page_service_returns_service(session_service_mock: MagicMock, project_service_mock: MagicMock):
    """Verify dependency returns SessionPageService."""
    service = await get_session_page_service(session_service=session_service_mock, project_service=project_service_mock)
    assert isinstance(service, SessionPageService)
    assert service.session_service is session_service_mock
    assert service.project_service is project_service_mock