from unittest.mock import MagicMock

from app.sessions.dependencies import get_session_repository, get_session_service, get_session_page_service
from app.sessions.repositories import ChatSessionRepository
from app.sessions.services import SessionService, SessionPageService


async def test_get_session_repository_returns_repo(db_session_mock):
    """Verify dependency returns ChatSessionRepository."""
    repo = await get_session_repository(db=db_session_mock)
    assert isinstance(repo, ChatSessionRepository)
    assert repo.db is db_session_mock


async def test_get_session_service_returns_service(db_session_mock):
    """Verify dependency returns SessionService."""
    service = await get_session_service(db=db_session_mock)
    assert isinstance(service, SessionService)
    assert service.session_repo.db is db_session_mock


async def test_get_session_page_service_returns_service(session_service_mock: MagicMock, project_service_mock: MagicMock):
    """Verify dependency returns SessionPageService."""
    service = await get_session_page_service(session_service=session_service_mock, project_service=project_service_mock)
    assert isinstance(service, SessionPageService)
    assert service.session_service is session_service_mock
    assert service.project_service is project_service_mock