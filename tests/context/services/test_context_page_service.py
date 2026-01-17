from unittest.mock import AsyncMock

import pytest

from app.context.models import ContextFile
from app.context.schemas import FileTreeNode
from app.context.services.page import ContextPageService
from app.projects.models import Project


@pytest.fixture
def service(workspace_service_mock, file_system_service_mock, project_service_mock):
    return ContextPageService(
        workspace_service_mock, file_system_service_mock, project_service_mock
    )


async def test_get_file_tree_no_project(service, project_service_mock):
    """Should return empty tree if no active project."""
    project_service_mock.get_active_project = AsyncMock(return_value=None)

    data = await service.get_file_tree_page_data(session_id=1)
    assert data == {"file_tree": {}}

    project_service_mock.get_active_project.assert_awaited_once_with()


async def test_get_file_tree_success(
    service, project_service_mock, workspace_service_mock, file_system_service_mock
):
    """Should return transformed tree with selection state."""
    # 1. Setup Project
    project_mock = Project(id=1, name="MyProject", path="/tmp/proj")
    project_service_mock.get_active_project = AsyncMock(return_value=project_mock)

    # 2. Setup File System Tree
    # Structure:
    # - root_file.py
    # - src/
    #   - main.py (Selected)
    file_system_service_mock.get_project_file_tree = AsyncMock(
        return_value=[
            FileTreeNode(name="root_file.py", path="root_file.py", is_dir=False),
            FileTreeNode(
                name="src",
                path="src",
                is_dir=True,
                children=[
                    FileTreeNode(name="main.py", path="src/main.py", is_dir=False)
                ],
            ),
        ]
    )

    # 3. Setup Active Context (Selected files)
    context_file = ContextFile(session_id=1, file_path="src/main.py")
    workspace_service_mock.get_active_context = AsyncMock(return_value=[context_file])

    # Execute
    data = await service.get_file_tree_page_data(session_id=1)

    # Assertions
    root = data["file_tree"]
    assert root["name"] == "MyProject"
    assert root["type"] == "folder"

    children = root["children"]
    assert len(children) == 2

    # Check root_file.py (Not Selected)
    root_file = next(c for c in children if c["name"] == "root_file.py")
    assert root_file["selected"] is False

    # Check src folder
    src_dir = next(c for c in children if c["name"] == "src")
    assert (
        "selected" not in src_dir
    )  # Folders don't get selected state usually, or depends on implementation

    # Check main.py (Selected)
    main_py = src_dir["children"][0]
    assert main_py["name"] == "main.py"
    assert main_py["selected"] is True

    # Verify interactions
    file_system_service_mock.get_project_file_tree.assert_awaited_once_with()
    workspace_service_mock.get_active_context.assert_awaited_once_with(1)
    project_service_mock.get_active_project.assert_awaited_once_with()


async def test_get_context_files_page_data(service, workspace_service_mock):
    """Should return active context files."""
    files = [
        ContextFile(id=1, session_id=99, file_path="a.py"),
        ContextFile(id=2, session_id=99, file_path="b.py"),
    ]
    workspace_service_mock.get_active_context = AsyncMock(return_value=files)

    data = await service.get_context_files_page_data(session_id=99)

    assert data["files"] == files
    assert data["session_id"] == 99
    workspace_service_mock.get_active_context.assert_awaited_once_with(99)
