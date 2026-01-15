import pytest
from unittest.mock import MagicMock

from app.sessions.factories import build_session_service
from app.sessions.services import SessionService
from app.sessions.repositories import ChatSessionRepository


async def test_build_session_service(mocker):
    """Verify factory wiring."""
    db_mock = mocker.Mock()

    # Mock the downstream factory call to avoid real DB interaction or dependency issues
    mock_project_service = MagicMock()
    mock_build_project_service = mocker.patch(
        "app.sessions.factories.build_project_service",
        new_callable=mocker.AsyncMock,
    )
    mock_build_project_service.return_value = mock_project_service

    service = await build_session_service(db=db_mock)

    assert isinstance(service, SessionService)
    assert isinstance(service.session_repo, ChatSessionRepository)
    assert service.session_repo.db is db_mock

    assert service.project_service is mock_project_service

    mock_build_project_service.assert_awaited_once_with(db_mock)
