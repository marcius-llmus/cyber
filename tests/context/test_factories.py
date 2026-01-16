from unittest.mock import AsyncMock
from app.context.factories import build_workspace_service, build_codebase_service
from app.context.services import WorkspaceService
from app.context.services.codebase import CodebaseService


async def test_build_workspace_service(db_session_mock, mocker):
    """Test building workspace service."""
    project_service_mock = mocker.MagicMock()
    codebase_service_mock = mocker.MagicMock()
    build_project_service_mock = mocker.patch(
        "app.context.factories.build_project_service",
        new=AsyncMock(return_value=project_service_mock),
    )
    build_codebase_service_mock = mocker.patch(
        "app.context.factories.build_codebase_service",
        new=AsyncMock(return_value=codebase_service_mock),
    )
    
    service = await build_workspace_service(db_session_mock)
    
    assert isinstance(service, WorkspaceService)
    assert service.context_repo.db is db_session_mock
    build_project_service_mock.assert_awaited_once_with(db_session_mock)
    build_codebase_service_mock.assert_awaited_once_with()


async def test_build_codebase_service():
    """Test building codebase service."""
    service = await build_codebase_service()
    assert isinstance(service, CodebaseService)