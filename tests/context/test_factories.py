from unittest.mock import AsyncMock

from app.context.factories import (
    build_codebase_service,
    build_filesystem_service,
    build_repo_map_service,
    build_search_service,
    build_workspace_service,
)
from app.context.services import (
    FileSystemService,
    RepoMapService,
    SearchService,
    WorkspaceService,
)
from app.context.services.codebase import CodebaseService
from app.projects.services import ProjectService


async def test_build_workspace_service(db_session_mock, mocker):
    """Test building workspace service."""
    project_service_mock = mocker.create_autospec(ProjectService, instance=True)
    codebase_service_mock = mocker.create_autospec(CodebaseService, instance=True)
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


async def test_build_repo_map_service(db_session_mock, mocker):
    """Test build_repo_map_service wires dependencies and threads db correctly."""
    workspace_service_mock = mocker.create_autospec(WorkspaceService, instance=True)
    project_service_mock = mocker.create_autospec(ProjectService, instance=True)
    codebase_service_mock = mocker.create_autospec(CodebaseService, instance=True)

    build_workspace_service_mock = mocker.patch(
        "app.context.factories.build_workspace_service",
        new=AsyncMock(return_value=workspace_service_mock),
    )
    build_project_service_mock = mocker.patch(
        "app.context.factories.build_project_service",
        new=AsyncMock(return_value=project_service_mock),
    )
    build_codebase_service_mock = mocker.patch(
        "app.context.factories.build_codebase_service",
        new=AsyncMock(return_value=codebase_service_mock),
    )

    service = await build_repo_map_service(db_session_mock)

    assert isinstance(service, RepoMapService)
    assert service.context_service is workspace_service_mock
    assert service.project_service is project_service_mock
    assert service.codebase_service is codebase_service_mock
    build_workspace_service_mock.assert_awaited_once_with(db_session_mock)
    build_project_service_mock.assert_awaited_once_with(db_session_mock)
    build_codebase_service_mock.assert_awaited_once_with()


async def test_build_search_service(db_session_mock, mocker):
    """Test build_search_service wires dependencies correctly."""
    mocker.patch("app.context.services.search.tiktoken.get_encoding")

    project_service_mock = mocker.create_autospec(ProjectService, instance=True)
    codebase_service_mock = mocker.create_autospec(CodebaseService, instance=True)

    build_project_service_mock = mocker.patch(
        "app.context.factories.build_project_service",
        new=AsyncMock(return_value=project_service_mock),
    )
    build_codebase_service_mock = mocker.patch(
        "app.context.factories.build_codebase_service",
        new=AsyncMock(return_value=codebase_service_mock),
    )

    service = await build_search_service(db_session_mock)

    assert isinstance(service, SearchService)
    assert service.project_service is project_service_mock
    assert service.codebase_service is codebase_service_mock
    build_project_service_mock.assert_awaited_once_with(db_session_mock)
    build_codebase_service_mock.assert_awaited_once_with()


async def test_build_filesystem_service(db_session_mock, mocker):
    """Test build_filesystem_service wires dependencies correctly."""
    project_service_mock = mocker.create_autospec(ProjectService, instance=True)
    codebase_service_mock = mocker.create_autospec(CodebaseService, instance=True)

    build_project_service_mock = mocker.patch(
        "app.context.factories.build_project_service",
        new=AsyncMock(return_value=project_service_mock),
    )
    build_codebase_service_mock = mocker.patch(
        "app.context.factories.build_codebase_service",
        new=AsyncMock(return_value=codebase_service_mock),
    )

    service = await build_filesystem_service(db_session_mock)

    assert isinstance(service, FileSystemService)
    assert service.project_service is project_service_mock
    assert service.codebase_service is codebase_service_mock
    build_project_service_mock.assert_awaited_once_with(db_session_mock)
    build_codebase_service_mock.assert_awaited_once_with()
