import pytest
from unittest.mock import MagicMock
from app.context.factories import build_workspace_service, build_codebase_service
from app.context.services import WorkspaceService
from app.context.services.codebase import CodebaseService


async def test_build_workspace_service(db_session_mock, mocker):
    """Test building workspace service."""
    mocker.patch("app.context.factories.build_project_service", return_value=MagicMock())
    mocker.patch("app.context.factories.build_codebase_service", return_value=MagicMock())
    
    service = await build_workspace_service(db_session_mock)
    
    assert isinstance(service, WorkspaceService)
    assert service.context_repo.db is db_session_mock


async def test_build_codebase_service():
    """Test building codebase service."""
    service = await build_codebase_service()
    assert isinstance(service, CodebaseService)