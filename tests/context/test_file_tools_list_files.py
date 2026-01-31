from unittest.mock import AsyncMock

from app.context.tools import FileTools


async def test_file_tools_list_files_supports_multiple_dirs(
    db_sessionmanager_mock, mocker, settings_snapshot
):
    mock_fs_service = AsyncMock()
    mock_fs_service.list_files = AsyncMock(
        return_value={
            "src": ["a.py", "b.py", "entity/"],
            "src/entity": ["c.py", "d.py"],
        }
    )

    mocker.patch(
        "app.context.tools.build_filesystem_service",
        new=AsyncMock(return_value=mock_fs_service),
    )

    tools = FileTools(
        db=db_sessionmanager_mock, settings_snapshot=settings_snapshot, session_id=1
    )

    out = await tools.list_files(["src", "src/entity"])

    assert out == "\n\n".join(
        [
            "## Directory: src\na.py\nb.py\nentity/",
            "## Directory: src/entity\nc.py\nd.py",
        ]
    )

    mock_fs_service.list_files.assert_awaited_once_with(["src", "src/entity"])


async def test_file_tools_list_files_empty_list_defaults_to_root(
    db_sessionmanager_mock, mocker, settings_snapshot
):
    mock_fs_service = AsyncMock()
    mock_fs_service.list_files = AsyncMock(return_value={".": ["root_file.txt"]})

    mocker.patch(
        "app.context.tools.build_filesystem_service",
        new=AsyncMock(return_value=mock_fs_service),
    )

    tools = FileTools(
        db=db_sessionmanager_mock, settings_snapshot=settings_snapshot, session_id=1
    )

    out = await tools.list_files([])

    assert out == "## Directory: .\nroot_file.txt"
    mock_fs_service.list_files.assert_awaited_once_with(["."])
