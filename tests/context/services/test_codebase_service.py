import pytest
from pathlib import Path
from app.context.services.codebase import CodebaseService
from app.context.schemas import FileStatus, FileTreeNode


async def test_is_ignored(temp_codebase):
    """Test is_ignored returns True for ignored files."""
    # IMPORTANT NOTE: we don't need a fixture for CodebaseService because it has no deps,
    # and it don't need to have any internal machinery mocked.
    service = CodebaseService()
    root = temp_codebase.root

    # 1. Explicitly ignored file
    assert await service.is_ignored(root, "ignore_me.txt") is True
    # 2. Ignored by extension
    assert await service.is_ignored(root, "logs/app.log") is True
    # 3. Ignored directory
    assert await service.is_ignored(root, "secret/config.json") is True
    # 4. Not ignored
    assert await service.is_ignored(root, "src/main.py") is False
    assert await service.is_ignored(root, "README.md") is False


async def test_validate_file_path(temp_codebase):
    """Test validate_file_path behavior."""
    service = CodebaseService()
    root = temp_codebase.root

    # 1. Valid file
    path = await service.validate_file_path(root, "src/main.py")
    assert path == Path(temp_codebase.main_py)

    # 2. Ignored file -> Raises ValueError
    with pytest.raises(ValueError, match="Access denied"):
        await service.validate_file_path(root, "ignore_me.txt")

    # 3. Outside file -> Raises ValueError
    with pytest.raises(ValueError, match="Access denied"):
        await service.validate_file_path(root, "../outside.txt")

    # 4. Directory -> Raises ValueError (expects file)
    with pytest.raises(ValueError, match="Path is not a file"):
        await service.validate_file_path(root, "src")

    # 5. Non-existent -> Raises ValueError (if must_exist=True)
    with pytest.raises(ValueError, match="File not found"):
        await service.validate_file_path(root, "ghost.py", must_exist=True)

    # 6. Non-existent -> OK (if must_exist=False)
    path = await service.validate_file_path(root, "new_file.py", must_exist=False)
    assert str(path).endswith("new_file.py")

async def test_validate_directory_path(temp_codebase):
    """Test validate_directory_path behavior."""
    service = CodebaseService()
    root = temp_codebase.root

    # 1. Valid dir
    path = await service.validate_directory_path(root, "src")
    assert path == Path(temp_codebase.src_dir)

    # 2. Ignored dir -> Raises ValueError
    with pytest.raises(ValueError, match="Access denied"):
        await service.validate_directory_path(root, "secret")

    # 3. Not a directory -> Raises ValueError
    with pytest.raises(ValueError, match="Path is not a directory"):
        await service.validate_directory_path(root, "src/main.py")

    # 4. Non-existent -> Raises ValueError
    with pytest.raises(ValueError, match="Directory not found"):
        await service.validate_directory_path(root, "ghost_dir")

async def test_list_dir(temp_codebase):
    """Test list_dir returns filtered file list."""
    service = CodebaseService()
    root = temp_codebase.root

    # Root listing
    results = await service.list_dir(root, ".")
    assert "README.md" in results
    assert "src/" in results
    assert "bin/" in results
    assert "ignore_me.txt" not in results
    assert "logs/" in results  # Directories are listed even if contents are ignored, unless dir is ignored

    # Subdir listing
    results = await service.list_dir(root, "src")
    assert "main.py" in results
    assert "utils.py" in results

async def test_read_file(temp_codebase):
    """Test read_file returns content."""
    service = CodebaseService()
    root = temp_codebase.root

    # 1. Text file
    result = await service.read_file(root, "src/main.py")
    assert result.status == FileStatus.SUCCESS
    assert "print" in result.content

    # 2. Binary file
    result = await service.read_file(root, "bin/data.bin")
    assert result.status == FileStatus.BINARY
    assert result.content is None

    # 3. Ignored file -> Error
    result = await service.read_file(root, "ignore_me.txt")
    assert result.status == FileStatus.ERROR
    assert "Access denied" in result.error_message

    # 4. Missing file -> Success (empty)
    result = await service.read_file(root, "missing.py", must_exist=False)
    assert result.status == FileStatus.SUCCESS
    assert result.content == ""

async def test_filter_and_resolve_paths(temp_codebase):
    """Test filtering of paths."""
    service = CodebaseService()
    root = temp_codebase.root

    inputs = [
        "src/main.py",          # Valid
        "ignore_me.txt",        # Ignored
        "../outside.txt",       # Outside
        "ghost.py"              # Missing
    ]
    
    # Note: filter_and_resolve_paths uses must_exist=True internally
    results = await service.filter_and_resolve_paths(root, inputs)
    
    assert len(results) == 1
    assert Path(temp_codebase.main_py).resolve() in [Path(p) for p in results]

async def test_resolve_file_patterns(temp_codebase):
    """Test resolving glob patterns."""
    service = CodebaseService()
    root = temp_codebase.root

    # 1. Exact match
    results = await service.resolve_file_patterns(root, ["src/main.py"])
    assert len(results) == 1
    assert "src/main.py" in results

    # 2. Glob match
    results = await service.resolve_file_patterns(root, ["src/*.py"])
    assert "src/main.py" in results
    assert "src/utils.py" in results

async def test_build_file_tree(temp_codebase):
    """Test tree building."""
    service = CodebaseService()
    root = temp_codebase.root

    tree = await service.build_file_tree(root)
    
    # Verify structure
    # Root should contain src/, bin/, README.md
    names = [node.name for node in tree]
    assert "src" in names
    assert "bin" in names
    assert "README.md" in names
    assert "logs" not in names  # Ignored
    
    # Check recursion
    src_node = next(n for n in tree if n.name == "src")
    assert src_node.is_dir
    assert len(src_node.children) == 2
    src_children = [c.name for c in src_node.children]
    assert "main.py" in src_children
    assert "utils.py" in src_children

async def test_write_file(temp_codebase):
    """Test writing files."""
    service = CodebaseService()
    root = temp_codebase.root

    # 1. Write new file
    await service.write_file(root, "new_file.txt", "Hello")
    result = await service.read_file(root, "new_file.txt")
    assert result.content == "Hello"

    # 2. Overwrite existing
    await service.write_file(root, "new_file.txt", "Updated")
    result = await service.read_file(root, "new_file.txt")
    assert result.content == "Updated"

    # 3. Create parent directories
    await service.write_file(root, "nested/dir/test.txt", "Deep")
    result = await service.read_file(root, "nested/dir/test.txt")
    assert result.content == "Deep"