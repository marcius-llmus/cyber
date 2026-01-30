from pathlib import Path

import pytest

from app.context.schemas import FileStatus
from app.context.services.codebase import CodebaseService


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
    assert (
        "logs/" in results
    )  # Directories are listed even if contents are ignored, unless dir is ignored

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
        "src/main.py",  # Valid
        "ignore_me.txt",  # Ignored
        "../outside.txt",  # Outside
        "ghost.py",  # Missing
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

    # Root should contain src/, bin/, README.md
    names = [node.name for node in tree]
    assert "src" in names
    assert "bin" in names
    assert "README.md" in names
    # logs directory itself is not ignored by current patterns, but its .log file is.
    # build_file_tree includes directories only if they have non-ignored children.
    assert "logs" not in names

    # Check recursion
    src_node = next(n for n in tree if n.name == "src")
    assert src_node.is_dir
    # src contains more than just main.py/utils.py in our fixture (regex_cases.txt, glob_cases/)
    assert len(src_node.children) >= 2
    src_children = [c.name for c in src_node.children]
    assert "main.py" in src_children
    assert "utils.py" in src_children
    assert "regex_cases.txt" in src_children
    assert "glob_cases" in src_children


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

    # 4. Create nested directories and file
    await service.write_file(temp_codebase.root, "new_dir/new_file.txt", "content")
    assert (Path(temp_codebase.root) / "new_dir/new_file.txt").exists()
    assert (Path(temp_codebase.root) / "new_dir/new_file.txt").read_text() == "content"


async def test_resolve_file_patterns_complex(temp_codebase):
    """Test complex glob pattern resolution."""
    service = CodebaseService()
    root = temp_codebase.root

    # 1. Directory expansion (should find files inside)
    files = await service.resolve_file_patterns(root, ["src/glob_cases"])
    assert any("normal.txt" in f for f in files)
    assert any("weird[name].txt" in f for f in files)

    # 2. Recursive wildcard
    files = await service.resolve_file_patterns(root, ["src/**/*.py"])
    assert any("main.py" in f for f in files)
    assert any("utils.py" in f for f in files)

    # 3. Literal vs Escaped Glob
    # "weird[name].txt" contains special glob chars [].
    # If passed literally, glob might treat [name] as character class.

    # Literal attempt (likely fails to match specific file, might match nothing or wrong thing)
    files_literal = await service.resolve_file_patterns(
        root, ["src/glob_cases/weird[name].txt"]
    )
    assert len(files_literal) == 0

    # Escaped attempt (Python glob uses [[] to escape [)
    files_escaped = await service.resolve_file_patterns(
        root, ["src/glob_cases/weird[[]name].txt"]
    )
    assert len(files_escaped) == 1
    assert files_escaped[0].endswith("weird[name].txt")

    # 4. Mixed valid and ignored
    # *.log is ignored. src/regex_cases.txt is valid.
    files = await service.resolve_file_patterns(
        root, ["src/regex_cases.txt", "logs/*.log"]
    )
    assert len(files) == 1
    assert "regex_cases.txt" in files[0]

    # 5. Non-existent file (should be ignored or handled gracefully)
    files = await service.resolve_file_patterns(root, ["nonexistent.txt"])
    assert len(files) == 0

    # 6. Absolute path input (should work if within root)
    # resolve_file_patterns returns relative paths
    abs_path = temp_codebase.regex_file
    files = await service.resolve_file_patterns(root, [abs_path])
    assert len(files) == 1
    assert files[0] == "src/regex_cases.txt"


async def test_resolve_file_patterns_respects_ignore_patterns(temp_codebase):
    """Verify extra ignore patterns exclude files."""
    service = CodebaseService()
    root = temp_codebase.root

    # Ignore all python files
    files = await service.resolve_file_patterns(
        root, ["src/**"], ignore_patterns=["*.py"]
    )
    assert not any(f.endswith(".py") for f in files)
    assert any(f.endswith(".txt") for f in files)


async def test_resolve_file_patterns_ignore_patterns_directory_prefix(temp_codebase):
    """Directory-style ignore patterns (ending with '/') should exclude all children."""
    service = CodebaseService()
    root = temp_codebase.root

    files = await service.resolve_file_patterns(root, ["."], ignore_patterns=["src/"])
    assert not any(f.startswith("src/") for f in files)
    assert "README.md" in files


async def test_resolve_file_patterns_ignore_patterns_nested_glob(temp_codebase):
    """GitWildMatch patterns like 'src/**/*.py' should exclude nested python files."""
    service = CodebaseService()
    root = temp_codebase.root

    files = await service.resolve_file_patterns(
        root,
        ["src"],
        ignore_patterns=["src/**/*.py"],
    )
    assert not any(f.endswith(".py") for f in files)
    assert any(f.endswith(".txt") for f in files)


async def test_resolve_file_patterns_ignore_patterns_exact_file(temp_codebase):
    """Exact file ignore patterns should exclude that file."""
    service = CodebaseService()
    root = temp_codebase.root

    files = await service.resolve_file_patterns(
        root,
        ["src"],
        ignore_patterns=["src/main.py"],
    )
    assert "src/main.py" not in files
    assert "src/utils.py" in files


async def test_resolve_file_patterns_ignore_patterns_ignores_empty_and_whitespace(
    temp_codebase,
):
    """Whitespace-only ignore patterns should be ignored (no effect)."""
    service = CodebaseService()
    root = temp_codebase.root

    baseline = await service.resolve_file_patterns(root, ["src/*.py"])
    files = await service.resolve_file_patterns(
        root,
        ["src/*.py"],
        ignore_patterns=["\n", "   ", "\t"],
    )
    assert files == baseline


async def test_resolve_file_patterns_defaults_to_scan_all_pattern(temp_codebase):
    """If patterns is None or empty, CodebaseService uses SCAN_ALL_PATTERN=['.'].

    This should return at least a few known non-ignored files from the project.
    """
    service = CodebaseService()
    root = temp_codebase.root

    # None => scan all
    files_none = await service.resolve_file_patterns(root, None)
    assert "README.md" in files_none
    assert "src/main.py" in files_none

    # [] => scan all
    files_empty = await service.resolve_file_patterns(root, [])
    assert "README.md" in files_empty
    assert "src/main.py" in files_empty


async def test_resolve_file_patterns_rejects_outside_root(temp_codebase):
    """Patterns attempting to resolve outside project root are rejected."""
    service = CodebaseService()
    root = temp_codebase.root

    with pytest.raises(ValueError, match=r"targets outside project root"):
        await service.resolve_file_patterns(root, ["../outside.txt"])


async def test_resolve_file_patterns_supports_deep_wildcard_segments(temp_codebase):
    """Verify glob patterns with deep wildcard segments like 'src/**/utils.py' work."""
    service = CodebaseService()
    root = temp_codebase.root

    files = await service.resolve_file_patterns(root, ["src/**/utils.py"])
    assert files == ["src/utils.py"]
