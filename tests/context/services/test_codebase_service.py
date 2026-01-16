import pytest
from pathlib import Path
from app.context.services.codebase import CodebaseService
from app.context.schemas import FileStatus


async def test_is_ignored_true(tmp_path):
    """Test is_ignored returns True for ignored files."""
    service = CodebaseService()
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.ignored")
    
    ignored_file = tmp_path / "test.ignored"
    ignored_file.touch()
    
    assert await service.is_ignored(tmp_path, "test.ignored") is True


async def test_is_ignored_false(tmp_path):
    """Test is_ignored returns False for non-ignored files."""
    service = CodebaseService()
    # No gitignore, or empty
    
    normal_file = tmp_path / "test.txt"
    normal_file.touch()
    
    assert await service.is_ignored(tmp_path, "test.txt") is False


async def test_validate_file_path_valid(tmp_path):
    """Test validate_file_path with valid path."""
    service = CodebaseService()
    file_path = tmp_path / "valid.txt"
    file_path.touch()
    
    result = await service.validate_file_path(str(tmp_path), "valid.txt")
    assert result == file_path.resolve()


async def test_validate_file_path_outside_root(tmp_path):
    """Test validate_file_path raises error for paths outside root."""
    service = CodebaseService()
    outside_file = tmp_path.parent / "outside.txt"
    
    # We pass '..' to try to go up
    with pytest.raises(ValueError, match="Access denied"):
        await service.validate_file_path(str(tmp_path), "../outside.txt")


async def test_validate_file_path_ignored(tmp_path):
    """Test validate_file_path raises error for ignored files."""
    service = CodebaseService()
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("*.secret")
    
    secret_file = tmp_path / "config.secret"
    secret_file.touch()
    
    with pytest.raises(ValueError, match="Access denied"):
        await service.validate_file_path(str(tmp_path), "config.secret")


async def test_validate_file_path_not_exist(tmp_path):
    """Test validate_file_path raises error if file does not exist."""
    service = CodebaseService()
    with pytest.raises(ValueError, match="File not found"):
        await service.validate_file_path(str(tmp_path), "non_existent.txt", must_exist=True)


async def test_list_dir(tmp_path):
    """Test list_dir returns filtered file list."""
    service = CodebaseService()
    (tmp_path / "file1.txt").touch()
    (tmp_path / "file2.ignored").touch()
    (tmp_path / "subdir").mkdir()
    (tmp_path / ".gitignore").write_text("*.ignored")
    
    results = await service.list_dir(str(tmp_path), ".")
    assert "file1.txt" in results
    assert "subdir/" in results
    assert "file2.ignored" not in results


async def test_read_file_success(tmp_path):
    """Test read_file returns content."""
    service = CodebaseService()
    file_path = tmp_path / "read_me.txt"
    file_path.write_text("Hello World", encoding="utf-8")
    
    result = await service.read_file(str(tmp_path), "read_me.txt")
    assert result.status == FileStatus.SUCCESS
    assert result.content == "Hello World"


async def test_read_file_binary(tmp_path):
    """Test read_file handles binary files."""
    service = CodebaseService()
    file_path = tmp_path / "binary.bin"
    with open(file_path, "wb") as f:
        f.write(b"\x80\x81")
        
    result = await service.read_file(str(tmp_path), "binary.bin")
    assert result.status == FileStatus.BINARY
    assert result.content is None