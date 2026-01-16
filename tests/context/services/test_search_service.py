import pytest
from unittest.mock import MagicMock
from app.context.services.search import SearchService
from app.projects.exceptions import ActiveProjectRequiredException
from app.context.schemas import FileReadResult, FileStatus

@pytest.fixture
def service(project_service_mock, codebase_service_mock, settings_service_mock, mocker):
    # Mock tiktoken to prevent network calls
    mocker.patch("tiktoken.get_encoding")
    return SearchService(project_service_mock, codebase_service_mock, settings_service_mock)

async def test_grep_no_project(service, project_service_mock):
    project_service_mock.get_active_project.return_value = None
    with pytest.raises(ActiveProjectRequiredException):
        await service.grep("pattern")

async def test_grep_empty_pattern_list(service, project_service_mock, settings_service_mock):
    project_service_mock.get_active_project.return_value = MagicMock()
    settings_service_mock.get_settings.return_value = MagicMock(grep_token_limit=1000)
    
    result = await service.grep([])
    assert result == "Error: Empty search pattern."

async def test_grep_success(service, project_service_mock, codebase_service_mock, settings_service_mock, mocker):
    # 1. Setup
    project_mock = MagicMock(path="/tmp")
    project_service_mock.get_active_project.return_value = project_mock
    settings_service_mock.get_settings.return_value = MagicMock(grep_token_limit=1000)
    
    codebase_service_mock.resolve_file_patterns.return_value = ["file.py"]
    codebase_service_mock.read_file.return_value = FileReadResult(
        file_path="file.py", content="def foo(): pass", status=FileStatus.SUCCESS
    )

    # 2. Patch TreeContext
    tree_cls = mocker.patch("app.context.services.search.TreeContext")
    tree_instance = tree_cls.return_value
    tree_instance.grep.return_value = [1] # Simulating matches
    tree_instance.format.return_value = "def foo(): pass"

    # 3. Execute
    result = await service.grep("foo")

    # 4. Assert
    assert "file.py:" in result
    assert "def foo(): pass" in result
    tree_instance.grep.assert_called_with("foo", ignore_case=True)

async def test_grep_no_matches(service, project_service_mock, codebase_service_mock, settings_service_mock, mocker):
    # 1. Setup
    project_service_mock.get_active_project.return_value = MagicMock(path="/tmp")
    settings_service_mock.get_settings.return_value = MagicMock(grep_token_limit=1000)
    codebase_service_mock.resolve_file_patterns.return_value = ["file.py"]
    codebase_service_mock.read_file.return_value = FileReadResult(
        file_path="file.py", content="content", status=FileStatus.SUCCESS
    )

    # 2. Patch TreeContext to return no matches
    tree_cls = mocker.patch("app.context.services.search.TreeContext")
    tree_instance = tree_cls.return_value
    tree_instance.grep.return_value = []

    # 3. Execute
    result = await service.grep("pattern")

    # 4. Assert
    assert result == "No matches found."

async def test_grep_token_limit(service, project_service_mock, codebase_service_mock, settings_service_mock, mocker):
    # 1. Setup
    project_service_mock.get_active_project.return_value = MagicMock(path="/tmp")
    settings_service_mock.get_settings.return_value = MagicMock(grep_token_limit=10) # Very small limit
    
    codebase_service_mock.resolve_file_patterns.return_value = ["file1.py", "file2.py"]
    codebase_service_mock.read_file.side_effect = [
        FileReadResult(file_path="file1.py", content="content1", status=FileStatus.SUCCESS),
        FileReadResult(file_path="file2.py", content="content2", status=FileStatus.SUCCESS)
    ]

    # 2. Patch TreeContext
    tree_cls = mocker.patch("app.context.services.search.TreeContext")
    tree_instance = tree_cls.return_value
    tree_instance.grep.return_value = [1]
    tree_instance.format.return_value = "long content that exceeds limit"
    
    # Mock encoding to return length > limit
    # service.encoding.encode is what is called. 
    # It's an instance attribute set in __init__. We can patch tiktoken.get_encoding or mock the attribute.
    service.encoding = MagicMock()
    service.encoding.encode.return_value = [1] * 20 # Length 20 > limit 10

    # 3. Execute
    result = await service.grep("pattern")

    # 4. Assert
    assert "truncated due to token limit" in result