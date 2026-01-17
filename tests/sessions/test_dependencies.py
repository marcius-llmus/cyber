from unittest.mock import AsyncMock, MagicMock

import pytest

from app.sessions.dependencies import (
    get_session_page_service,
    get_session_repository,
    get_session_service,
)
from app.sessions.repositories import ChatSessionRepository
from app.sessions.services import SessionPageService


async def test_get_session_repository_returns_repo(db_session_mock):
    """Verify dependency returns ChatSessionRepository."""
    repo = await get_session_repository(db=db_session_mock)
    assert isinstance(repo, ChatSessionRepository)
    assert repo.db is db_session_mock


async def test_get_session_service_returns_service(
    db_session_mock, mocker, session_service_mock
):
    """Verify dependency delegates to build_session_service and returns its result."""
    build_session_service_mock = mocker.patch(
        "app.sessions.dependencies.build_session_service",
        new=AsyncMock(return_value=session_service_mock),
    )

    service = await get_session_service(db=db_session_mock)

    assert service is session_service_mock
    build_session_service_mock.assert_awaited_once_with(db_session_mock)


async def test_get_session_service_propagates_error(db_session_mock, mocker):
    """Verify dependency propagates errors from build_session_service."""
    build_session_service_mock = mocker.patch(
        "app.sessions.dependencies.build_session_service",
        new=AsyncMock(side_effect=ValueError("Boom")),
    )

    with pytest.raises(ValueError, match="Boom"):
        await get_session_service(db=db_session_mock)

    build_session_service_mock.assert_awaited_once_with(db_session_mock)


async def test_get_session_page_service_returns_service(
    session_service_mock: MagicMock, project_service_mock: MagicMock
):
    """Verify dependency returns SessionPageService."""
    service = await get_session_page_service(
        session_service=session_service_mock, project_service=project_service_mock
    )
    assert isinstance(service, SessionPageService)
    assert service.session_service is session_service_mock
    assert service.project_service is project_service_mock
