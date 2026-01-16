import pytest
from unittest.mock import AsyncMock

from app.sessions.factories import build_session_service
from app.sessions.repositories import ChatSessionRepository
from app.sessions.services import SessionService


async def test_build_session_service_wires_repo_and_project_service(db_session_mock, mocker, project_service_mock):
    """Verify factory constructs repo and awaits build_project_service, wiring the result."""
    build_project_service_mock = mocker.patch(
        "app.sessions.factories.build_project_service",
        new=AsyncMock(return_value=project_service_mock),
    )

    service = await build_session_service(db=db_session_mock)

    assert isinstance(service, SessionService)
    assert isinstance(service.session_repo, ChatSessionRepository)
    assert service.session_repo.db is db_session_mock
    assert service.project_service is project_service_mock

    build_project_service_mock.assert_awaited_once_with(db_session_mock)


async def test_build_session_service_propagates_error_from_project_factory(db_session_mock, mocker):
    """Verify build_session_service propagates errors from build_project_service."""
    build_project_service_mock = mocker.patch(
        "app.sessions.factories.build_project_service",
        new=AsyncMock(side_effect=ValueError("Boom")),
    )

    with pytest.raises(ValueError, match="Boom"):
        await build_session_service(db=db_session_mock)

    build_project_service_mock.assert_awaited_once_with(db_session_mock)