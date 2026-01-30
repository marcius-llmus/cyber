from unittest.mock import AsyncMock

from app.context.tools import FileTools


async def test_file_tools_list_files_supports_multiple_dirs(
    db_sessionmanager_mock, mocker, settings_snapshot
):
    mock_fs_service = AsyncMock()
    mock_fs_service.list_files = AsyncMock(return_value=["a.py", "b.py", "c/"])

    mocker.patch(
        "app.context.tools.build_filesystem_service",
        new=AsyncMock(return_value=mock_fs_service),
    )

    tools = FileTools(
        db=db_sessionmanager_mock, settings_snapshot=settings_snapshot, session_id=1
    )

    out = await tools.list_files(["src", "tests"])

    assert "## Directory: src" in out
    assert "a.py" in out
    assert "## Directory: tests" in out
    assert "b.py" in out
    assert "c/" in out

    mock_fs_service.list_files.assert_awaited_once_with(["src", "tests"])


async def test_file_tools_list_files_empty_list_defaults_to_root(
    db_sessionmanager_mock, mocker, settings_snapshot
):
    mock_fs_service = AsyncMock()
    mock_fs_service.list_files = AsyncMock(return_value=["root_file.txt"])

    mocker.patch(
        "app.context.tools.build_filesystem_service",
        new=AsyncMock(return_value=mock_fs_service),
    )

    tools = FileTools(
        db=db_sessionmanager_mock, settings_snapshot=settings_snapshot, session_id=1
    )

    out = await tools.list_files([])

    assert "root_file.txt" in out
    mock_fs_service.list_files.assert_awaited_once_with(["."])
