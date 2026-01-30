from unittest.mock import AsyncMock

import pytest

from app.context.tools import FileTools


@pytest.mark.skip
async def test_file_tools_list_files_supports_multiple_dirs(
    db_sessionmanager_mock, mocker, settings_snapshot
):
    mock_fs_service = AsyncMock()
    mock_fs_service.list_files.side_effect = [["a.py"], ["b.py", "c/"]]

    mocker.patch(
        "app.context.tools.build_filesystem_service",
        new=AsyncMock(return_value=mock_fs_service),
    )

    tools = FileTools(db=db_sessionmanager_mock, settings_snapshot=settings_snapshot, session_id=1)

    out = await tools.list_files(["src", "tests"])

    assert "## Directory: src" in out
    assert "a.py" in out
    assert "## Directory: tests" in out
    assert "b.py" in out
    assert "c/" in out
    
    assert mock_fs_service.list_files.call_count == 2
    mock_fs_service.list_files.assert_any_call("src")
    mock_fs_service.list_files.assert_any_call("tests")


@pytest.mark.skip
async def test_file_tools_list_files_empty_list_is_error(
    db_sessionmanager_mock, settings_snapshot
):
    tools = FileTools(db=db_sessionmanager_mock, settings_snapshot=settings_snapshot, session_id=1)

    out = await tools.list_files([])
    assert "Error: dir_paths cannot be empty." in out
