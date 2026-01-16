import pytest
from unittest.mock import MagicMock
from app.context.services import WorkspaceService
from app.context.models import ContextFile
from app.context.schemas import ContextFileUpdate
from app.patches.schemas import ParsedDiffPatch
from app.projects.exceptions import ActiveProjectRequiredException


async def test_add_file_success(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock, project_mock
):
    """Test adding a file to context."""
    project_service_mock.get_active_project.return_value = project_mock
    context_repository_mock.get_by_session_and_path.return_value = None
    
    mock_file = ContextFile(session_id=chat_session_mock.id, file_path="new.py")
    context_repository_mock.create.return_value = mock_file

    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    
    result = await service.add_file(chat_session_mock.id, "new.py")
    
    assert result == mock_file
    codebase_service_mock.validate_file_path.assert_awaited_once_with(
        project_mock.path, "new.py", must_exist=True
    )
    context_repository_mock.create.assert_awaited_once()


async def test_add_file_no_project(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock
):
    """Test add_file fails without active project."""
    project_service_mock.get_active_project.return_value = None
    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    
    with pytest.raises(ActiveProjectRequiredException):
        await service.add_file(chat_session_mock.id, "file.py")


async def test_add_file_invalid_path(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock, project_mock
):
    """Test add_file fails if path is invalid."""
    project_service_mock.get_active_project.return_value = project_mock
    codebase_service_mock.validate_file_path.side_effect = ValueError("Invalid path")
    
    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    
    with pytest.raises(ValueError, match="Invalid path"):
        await service.add_file(chat_session_mock.id, "bad.py")


async def test_add_file_existing(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock, context_file, project_mock
):
    """Test add_file updates hit count if file exists."""
    project_service_mock.get_active_project.return_value = project_mock
    context_repository_mock.get_by_session_and_path.return_value = context_file
    context_repository_mock.update.return_value = context_file
    
    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    
    result = await service.add_file(chat_session_mock.id, context_file.file_path)
    
    assert result == context_file
    context_repository_mock.update.assert_awaited_once()
    # Check that hit_count was incremented in the update call
    call_args = context_repository_mock.update.call_args
    assert call_args.kwargs['obj_in'].hit_count == context_file.hit_count + 1


async def test_remove_file(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock, context_file
):
    """Test removing a file from context."""
    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    
    await service.remove_file(chat_session_mock.id, context_file.id)
    
    context_repository_mock.delete_by_session_and_id.assert_awaited_once_with(
        chat_session_mock.id, context_file.id
    )


async def test_sync_files(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock, project_mock
):
    """Test syncing context files."""
    project_service_mock.get_active_project.return_value = project_mock
    
    # Codebase returns absolute paths
    codebase_service_mock.filter_and_resolve_paths.return_value = {
        f"{project_mock.path}/file1.py",
        f"{project_mock.path}/file2.py"
    }
    
    # Current context empty
    context_repository_mock.list_by_session.return_value = []
    # sync_files -> add_context_files -> add_file -> validate_file_path + get_by_session_and_path + create
    context_repository_mock.get_by_session_and_path.return_value = None
    # validate_file_path returns an absolute Path in real code; match the contract.
    async def _validate(project_root: str, file_path: str, must_exist: bool = True):
        return f"{project_mock.path}/{file_path}"

    codebase_service_mock.validate_file_path.side_effect = _validate

    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)

    await service.sync_files(chat_session_mock.id, ["file1.py", "file2.py"])

    assert context_repository_mock.create.await_count == 2

    created_paths = {call.kwargs["obj_in"].file_path for call in context_repository_mock.create.await_args_list}
    assert created_paths == {"file1.py", "file2.py"}


async def test_sync_context_for_diff_add(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock, project_mock
):
    """Test sync_context_for_diff with added file."""
    project_service_mock.get_active_project.return_value = project_mock
    # Mock add_file internal call logic (it calls validate and create)
    # Easier to just let it run since we mocked repo/codebase
    context_repository_mock.get_by_session_and_path.return_value = None
    
    patch = MagicMock(spec=ParsedDiffPatch)
    patch.is_added_file = True
    patch.is_removed_file = False
    patch.is_rename = False
    patch.path = "added.py"

    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    await service.sync_context_for_diff(session_id=chat_session_mock.id, patch=patch)

    # Should call add_file logic -> create
    context_repository_mock.create.assert_awaited_once()
    assert context_repository_mock.create.call_args.kwargs['obj_in'].file_path == "added.py"


async def test_sync_context_for_diff_remove(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock, project_mock
):
    """Test sync_context_for_diff with removed file."""
    project_service_mock.get_active_project.return_value = project_mock
    
    patch = MagicMock(spec=ParsedDiffPatch)
    patch.is_added_file = False
    patch.is_removed_file = True
    patch.is_rename = False
    patch.path = "removed.py"

    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    await service.sync_context_for_diff(session_id=chat_session_mock.id, patch=patch)

    # Should call remove_context_files_by_path -> delete_by_session_and_path
    context_repository_mock.delete_by_session_and_path.assert_awaited_once_with(chat_session_mock.id, "removed.py")


async def test_sync_context_for_diff_modified_ignored(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock
):
    """Test sync_context_for_diff ignores modified files."""
    patch = MagicMock(spec=ParsedDiffPatch)
    patch.is_added_file = False
    patch.is_removed_file = False
    patch.is_rename = False
    # imply modified

    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    await service.sync_context_for_diff(session_id=chat_session_mock.id, patch=patch)

    context_repository_mock.create.assert_not_called()
    context_repository_mock.delete_by_session_and_path.assert_not_called()


async def test_get_active_file_paths_abs(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock
):
    """Test getting absolute paths for active context."""
    f1 = ContextFile(session_id=chat_session_mock.id, file_path="f1.py")
    f2 = ContextFile(session_id=chat_session_mock.id, file_path="f2.ignored")
    
    context_repository_mock.list_by_session.return_value = [f1, f2]
    
    # Mock is_ignored
    async def side_effect_is_ignored(root, path):
        return "ignored" in path
    
    codebase_service_mock.is_ignored.side_effect = side_effect_is_ignored
    
    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    result = await service.get_active_file_paths_abs(chat_session_mock.id, "/root")
    
    assert len(result) == 1
    assert result[0] == "/root/f1.py"

async def test_delete_context_for_session(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock
):
    """Test deleting all context for a session."""
    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    await service.delete_context_for_session(chat_session_mock.id)
    context_repository_mock.delete_all_by_session.assert_awaited_once_with(chat_session_mock.id)

async def test_get_active_context(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock
):
    """Test getting active context."""
    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    await service.get_active_context(chat_session_mock.id)
    context_repository_mock.list_by_session.assert_awaited_once_with(chat_session_mock.id)

async def test_add_context_files(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock, project_mock
):
    """Test adding multiple files, handling errors gracefully."""
    project_service_mock.get_active_project.return_value = project_mock
    context_repository_mock.get_by_session_and_path.return_value = None
    
    # Mock validate to fail for second file
    async def _validate(root, path, must_exist=True):
        if "bad" in path:
            raise ValueError("Bad path")
        return f"{root}/{path}"
    
    codebase_service_mock.validate_file_path.side_effect = _validate
    
    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    await service.add_context_files(chat_session_mock.id, ["good.py", "bad.py", "good2.py"])
    
    # Should have tried to create 2 files (good.py and good2.py)
    assert context_repository_mock.create.await_count == 2

async def test_remove_context_files_by_path(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock
):
    """Test removing multiple files by path."""
    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    await service.remove_context_files_by_path(chat_session_mock.id, ["f1.py", "f2.py"])
    
    assert context_repository_mock.delete_by_session_and_path.await_count == 2
    # Verify calls
    calls = context_repository_mock.delete_by_session_and_path.await_args_list
    assert calls[0].args == (chat_session_mock.id, "f1.py")
    assert calls[1].args == (chat_session_mock.id, "f2.py")

async def test_sync_files_remove(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock, project_mock
):
    """Test sync_files removes files not in the list."""
    project_service_mock.get_active_project.return_value = project_mock
    
    # Incoming list is empty (so remove everything)
    codebase_service_mock.filter_and_resolve_paths.return_value = set()
    
    # Current context has 1 file
    f1 = ContextFile(session_id=chat_session_mock.id, file_path="old.py")
    context_repository_mock.list_by_session.return_value = [f1]
    
    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    await service.sync_files(chat_session_mock.id, [])
    
    context_repository_mock.delete_by_session_and_path.assert_awaited_once_with(
        chat_session_mock.id, "old.py"
    )

async def test_sync_files_no_project(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock
):
    """Test sync_files requires active project."""
    project_service_mock.get_active_project.return_value = None
    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    with pytest.raises(ActiveProjectRequiredException):
        await service.sync_files(chat_session_mock.id, [])

async def test_sync_context_for_diff_no_project(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock
):
    """Test sync_context_for_diff requires active project."""
    project_service_mock.get_active_project.return_value = None
    patch = MagicMock(spec=ParsedDiffPatch)
    patch.is_added_file = True
    
    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    with pytest.raises(ActiveProjectRequiredException):
        await service.sync_context_for_diff(session_id=chat_session_mock.id, patch=patch)

async def test_sync_context_for_diff_add(
    context_repository_mock, codebase_service_mock, project_service_mock, chat_session_mock, project_mock
):
    """Test sync_context_for_diff with added file."""
    project_service_mock.get_active_project.return_value = project_mock
    # Mock add_file internal call logic (it calls validate and create)
    # Easier to just let it run since we mocked repo/codebase
    context_repository_mock.get_by_session_and_path.return_value = None
    
    patch = MagicMock(spec=ParsedDiffPatch)
    patch.is_added_file = True
    patch.is_removed_file = False
    patch.is_rename = False
    patch.path = "added.py"

    service = WorkspaceService(project_service_mock, context_repository_mock, codebase_service_mock)
    await service.sync_context_for_diff(session_id=chat_session_mock.id, patch=patch)

    # Should call add_file logic -> create
    context_repository_mock.create.assert_awaited_once()
    assert context_repository_mock.create.call_args.kwargs['obj_in'].file_path == "added.py"