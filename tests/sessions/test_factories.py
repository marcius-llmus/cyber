import pytest
from unittest.mock import MagicMock

from app.sessions.factories import build_session_service
from app.sessions.services import SessionService
from app.sessions.repositories import ChatSessionRepository


async def test_build_session_service(mocker):
    """Verify factory wiring."""
    db_mock = mocker.Mock()
    
    # Mock the downstream factory call to avoid real DB interaction or dependency issues
    mocker.patch("app.sessions.factories.build_project_service", return_value=MagicMock())
    
    service = await build_session_service(db=db_mock)
    
    assert isinstance(service, SessionService)
    assert isinstance(service.session_repo, ChatSessionRepository)
    assert service.session_repo.db is db_mock
    
    # Check if project service is wired (it might be a real instance or mock depending on environment, 
    # but factory usually creates real instances)
    assert service.project_service is not None