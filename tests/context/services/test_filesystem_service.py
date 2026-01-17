import pytest
from unittest.mock import AsyncMock, MagicMock
from app.context.services.filesystem import FileSystemService
from app.projects.exceptions import ActiveProjectRequiredException
from app.context.schemas import FileTreeNode, FileReadResult, FileStatus
from app.projects.models import Project


@pytest.fixture
def service(project_service_mock, codebase_service_mock):
    return FileSystemService(project_service_mock, codebase_service_mock)


async def test_read_file_no_project(service, project_service_mock):
    project_service_mock.get_active_project = AsyncMock(return_value=None)
    with pytest.raises(ActiveProjectRequiredException):
        await service.read_file("test.py")

    project_service_mock.get_active_project.assert_awaited_once_with()


async def test_read_file_success(service, project_service_mock, codebase_service_mock):
    project = Project(id=1, name="p", path="/tmp/proj")
    project_service_mock.get_active_project = AsyncMock(return_value=project)
    expected = FileReadResult(file_path="test.py", status=FileStatus.SUCCESS)
    codebase_service_mock.read_file = AsyncMock(return_value=expected)

    result = await service.read_file("test.py")
    
    assert result == expected
    codebase_service_mock.read_file.assert_awaited_once_with("/tmp/proj", "test.py")
    project_service_mock.get_active_project.assert_awaited_once_with()


async def test_read_files_no_project(service, project_service_mock):
    project_service_mock.get_active_project = AsyncMock(return_value=None)
    with pytest.raises(ActiveProjectRequiredException):
        await service.read_files(["*.py"])

    project_service_mock.get_active_project.assert_awaited_once_with()


async def test_read_files_success(service, project_service_mock, codebase_service_mock):
    project = Project(id=1, name="p", path="/tmp/proj")
    project_service_mock.get_active_project = AsyncMock(return_value=project)
    
    # Mock resolution and reading
    codebase_service_mock.resolve_file_patterns = AsyncMock(return_value=["a.py", "b.py"])
    codebase_service_mock.read_files = AsyncMock(return_value=[object(), object()])
    
    await service.read_files(["*.py"])
    
    codebase_service_mock.resolve_file_patterns.assert_awaited_once_with("/tmp/proj", ["*.py"])
    codebase_service_mock.read_files.assert_awaited_once_with("/tmp/proj", ["a.py", "b.py"])
    project_service_mock.get_active_project.assert_awaited_once_with()


async def test_list_files_no_project(service, project_service_mock):
    project_service_mock.get_active_project = AsyncMock(return_value=None)
    with pytest.raises(ActiveProjectRequiredException):
        await service.list_files()

    project_service_mock.get_active_project.assert_awaited_once_with()


async def test_list_files_success(service, project_service_mock, codebase_service_mock):
    project = Project(id=1, name="p", path="/tmp/proj")
    project_service_mock.get_active_project = AsyncMock(return_value=project)
    codebase_service_mock.list_dir = AsyncMock(return_value=["file.txt"])
    
    result = await service.list_files("subdir")
    
    assert result == ["file.txt"]
    codebase_service_mock.list_dir.assert_awaited_once_with("/tmp/proj", "subdir")
    project_service_mock.get_active_project.assert_awaited_once_with()


async def test_write_file_no_project(service, project_service_mock):
    project_service_mock.get_active_project = AsyncMock(return_value=None)
    with pytest.raises(ActiveProjectRequiredException):
        await service.write_file("test.py", "content")

    project_service_mock.get_active_project.assert_awaited_once_with()


async def test_write_file_success(service, project_service_mock, codebase_service_mock):
    project_service_mock.get_active_project = AsyncMock(return_value=Project(id=1, name="p", path="/tmp/proj"))
    
    await service.write_file("test.py", "content")
    
    codebase_service_mock.write_file.assert_awaited_once_with("/tmp/proj", "test.py", "content")
    project_service_mock.get_active_project.assert_awaited_once_with()


async def test_get_project_file_tree_no_project(service, project_service_mock):
    project_service_mock.get_active_project = AsyncMock(return_value=None)
    result = await service.get_project_file_tree()
    assert result == []
    project_service_mock.get_active_project.assert_awaited_once_with()


async def test_get_project_file_tree_success(service, project_service_mock, codebase_service_mock):
    project_service_mock.get_active_project = AsyncMock(return_value=Project(id=1, name="p", path="/tmp/proj"))
    tree = [FileTreeNode(name="root", path="root", is_dir=True)]
    codebase_service_mock.build_file_tree = AsyncMock(return_value=tree)
    
    result = await service.get_project_file_tree()
    
    assert result == tree
    codebase_service_mock.build_file_tree.assert_awaited_once_with("/tmp/proj")
    project_service_mock.get_active_project.assert_awaited_once_with()