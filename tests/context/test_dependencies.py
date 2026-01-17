from unittest.mock import AsyncMock

from app.context.dependencies import (
    get_context_page_service,
    get_context_repository,
    get_context_service,
    get_filesystem_service,
)
from app.context.repositories import ContextRepository
from app.context.services import ContextPageService, FileSystemService, WorkspaceService
from app.projects.services import ProjectService


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


async def test_get_filesystem_service(db_session_mock, mocker):
    """Test get_filesystem_service dependency delegates to factory."""
    mock_service = mocker.create_autospec(FileSystemService, instance=True)
    build_filesystem_service_mock = mocker.patch(
        "app.context.dependencies.build_filesystem_service",
        new=AsyncMock(return_value=mock_service),
    )

    service = await get_filesystem_service(db_session_mock)

    assert service is mock_service
    build_filesystem_service_mock.assert_awaited_once_with(db_session_mock)


async def test_get_context_page_service(mocker):
    """Test get_context_page_service returns a ContextPageService wired from deps."""
    context_service_mock = mocker.create_autospec(WorkspaceService, instance=True)
    fs_service_mock = mocker.create_autospec(FileSystemService, instance=True)
    project_service_mock = mocker.create_autospec(ProjectService, instance=True)

    service = await get_context_page_service(
        context_service=context_service_mock,
        fs_service=fs_service_mock,
        project_service=project_service_mock,
    )

    assert isinstance(service, ContextPageService)
    assert service.context_service is context_service_mock
    assert service.fs_service is fs_service_mock
    assert service.project_service is project_service_mock
