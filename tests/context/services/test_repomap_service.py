from types import SimpleNamespace
import pytest
from unittest.mock import MagicMock
from unittest.mock import AsyncMock
from app.context.services.repomap import RepoMapService
from app.projects.exceptions import ActiveProjectRequiredException

@pytest.fixture
def service(workspace_service_mock, codebase_service_mock, settings_service_mock):
    return RepoMapService(workspace_service_mock, codebase_service_mock, settings_service_mock)

async def test_generate_repo_map_no_project(service, workspace_service_mock):
    workspace_service_mock.project_service.get_active_project = AsyncMock(return_value=None)
    with pytest.raises(ActiveProjectRequiredException):
        await service.generate_repo_map(session_id=1)

    workspace_service_mock.project_service.get_active_project.assert_awaited_once_with()

async def test_generate_repo_map_success(
    service, 
    workspace_service_mock, 
    codebase_service_mock, 
    settings_service_mock, 
    mocker
):
    # 1. Setup Mocks
    project_mock = MagicMock(path="/tmp/proj")
    workspace_service_mock.project_service.get_active_project = AsyncMock(return_value=project_mock)
    
    # Codebase returns relative paths
    codebase_service_mock.resolve_file_patterns = AsyncMock(return_value=["src/main.py", "README.md"])
    
    # Context returns absolute paths
    workspace_service_mock.get_active_file_paths_abs = AsyncMock(return_value=["/tmp/proj/src/main.py"])
    
    # Mentioned files resolution
    codebase_service_mock.filter_and_resolve_paths = AsyncMock(return_value={"/tmp/proj/other.py"})
    
    # Settings
    settings_service_mock.get_settings = AsyncMock(return_value=SimpleNamespace(ast_token_limit=2000))
    
    # Patch RepoMap
    repomap_cls = mocker.patch("app.context.services.repomap.RepoMap")
    repomap_instance = repomap_cls.return_value
    repomap_instance.generate = AsyncMock(return_value="Repo Map Content")

    # 2. Execute
    result = await service.generate_repo_map(
        session_id=1,
        mentioned_filenames={"other.py"}, 
        mentioned_idents={"Foo", "Bar"},
        include_active_content=False
    )

    # 3. Assert
    assert result == "Repo Map Content"
    
    # Check constructor call
    repomap_cls.assert_called_once()
    _, kwargs = repomap_cls.call_args
    assert kwargs["root"] == "/tmp/proj"
    assert "/tmp/proj/src/main.py" in kwargs["all_files"]
    assert "/tmp/proj/README.md" in kwargs["all_files"]
    assert kwargs["active_context_files"] == ["/tmp/proj/src/main.py"]
    assert kwargs["mentioned_filenames"] == {"/tmp/proj/other.py"}
    assert kwargs["mentioned_idents"] == {"Foo", "Bar"}
    assert kwargs["token_limit"] == 2000
    
    repomap_instance.generate.assert_awaited_once_with(include_active_content=False)

    workspace_service_mock.project_service.get_active_project.assert_awaited_once_with()
    codebase_service_mock.resolve_file_patterns.assert_awaited_once_with("/tmp/proj")
    workspace_service_mock.get_active_file_paths_abs.assert_awaited_once_with(1, "/tmp/proj")
    codebase_service_mock.filter_and_resolve_paths.assert_awaited_once_with("/tmp/proj", ["other.py"])
    settings_service_mock.get_settings.assert_awaited_once_with()