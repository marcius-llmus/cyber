import pytest
from unittest.mock import AsyncMock

from app.context.dependencies import get_context_repository, get_context_service
from app.context.repositories import ContextRepository
from app.context.services import WorkspaceService


async def test_get_context_repository(db_session_mock):
    """Test get_context_repository dependency."""
    repo = await get_context_repository(db_session_mock)
    assert isinstance(repo, ContextRepository)
    assert repo.db is db_session_mock


async def test_get_context_service(db_session_mock, mocker):
    """Test get_context_service dependency."""
    mock_service = mocker.create_autospec(WorkspaceService, instance=True)
    build_workspace_service_mock = mocker.patch(
        "app.context.dependencies.build_workspace_service",
        new=AsyncMock(return_value=mock_service),
    )
    
    service = await get_context_service(db_session_mock)
    
    assert service is mock_service
    build_workspace_service_mock.assert_awaited_once_with(db_session_mock)