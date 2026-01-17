from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.context.schemas import FileReadResult, FileStatus
from app.context.services.search import SearchService
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.models import Project
from app.settings.models import Settings


@pytest.fixture
def mock_tiktoken(mocker):
    mocker.patch("tiktoken.get_encoding")

@pytest.fixture
def service(project_service_mock, codebase_service_mock, settings_service_mock, mocker):
    # Mock tiktoken to prevent network calls
    mocker.patch("tiktoken.get_encoding")
    return SearchService(project_service_mock, codebase_service_mock, settings_service_mock)

async def test_grep_no_project(service, project_service_mock):
    project_service_mock.get_active_project = AsyncMock(return_value=None)
    with pytest.raises(ActiveProjectRequiredException):
        await service.grep("pattern")

async def test_grep_empty_pattern_list(service, project_service_mock, settings_service_mock):
    project_service_mock.get_active_project = AsyncMock(return_value=Project(id=1, name="p", path="/tmp"))
    settings_service_mock.get_settings = AsyncMock(return_value=Settings(max_history_length=0, ast_token_limit=0, grep_token_limit=1000, diff_patches_auto_open=True, diff_patches_auto_apply=True, coding_llm_temperature=0.0))

    result = await service.grep([])
    assert result == "Error: Empty search pattern."

    project_service_mock.get_active_project.assert_awaited_once_with()
    settings_service_mock.get_settings.assert_awaited_once_with()

async def test_grep_success(service, project_service_mock, codebase_service_mock, settings_service_mock, mocker):
    # 1. Setup
    project_service_mock.get_active_project = AsyncMock(return_value=Project(id=1, name="p", path="/tmp"))
    settings_service_mock.get_settings = AsyncMock(return_value=Settings(max_history_length=0, ast_token_limit=0, grep_token_limit=1000, diff_patches_auto_open=True, diff_patches_auto_apply=True, coding_llm_temperature=0.0))

    codebase_service_mock.resolve_file_patterns = AsyncMock(return_value=["file.py"])
    codebase_service_mock.read_file = AsyncMock(return_value=FileReadResult(
        file_path="file.py", content="def foo(): pass", status=FileStatus.SUCCESS
    ))

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

    project_service_mock.get_active_project.assert_awaited_once_with()
    settings_service_mock.get_settings.assert_awaited_once_with()
    codebase_service_mock.resolve_file_patterns.assert_awaited_once_with("/tmp", None)
    codebase_service_mock.read_file.assert_awaited_once_with("/tmp", "file.py")

async def test_grep_no_matches(service, project_service_mock, codebase_service_mock, settings_service_mock, mocker):
    # 1. Setup
    project_service_mock.get_active_project = AsyncMock(return_value=Project(id=1, name="p", path="/tmp"))
    settings_service_mock.get_settings = AsyncMock(return_value=Settings(max_history_length=0, ast_token_limit=0, grep_token_limit=1000, diff_patches_auto_open=True, diff_patches_auto_apply=True, coding_llm_temperature=0.0))
    codebase_service_mock.resolve_file_patterns = AsyncMock(return_value=["file.py"])
    codebase_service_mock.read_file = AsyncMock(return_value=FileReadResult(
        file_path="file.py", content="content", status=FileStatus.SUCCESS
    ))

    # 2. Patch TreeContext to return no matches
    tree_cls = mocker.patch("app.context.services.search.TreeContext")
    tree_instance = tree_cls.return_value
    tree_instance.grep.return_value = []

    # 3. Execute
    result = await service.grep("pattern")

    # 4. Assert
    assert result == "No matches found."

    project_service_mock.get_active_project.assert_awaited_once_with()
    settings_service_mock.get_settings.assert_awaited_once_with()
    codebase_service_mock.resolve_file_patterns.assert_awaited_once_with("/tmp", None)
    codebase_service_mock.read_file.assert_awaited_once_with("/tmp", "file.py")

async def test_grep_token_limit(service, project_service_mock, codebase_service_mock, settings_service_mock, mocker):
    # 1. Setup
    project_service_mock.get_active_project = AsyncMock(return_value=Project(id=1, name="p", path="/tmp"))
    settings_service_mock.get_settings = AsyncMock(return_value=Settings(max_history_length=0, ast_token_limit=0, grep_token_limit=10, diff_patches_auto_open=True, diff_patches_auto_apply=True, coding_llm_temperature=0.0))  # Very small limit

    codebase_service_mock.resolve_file_patterns = AsyncMock(return_value=["file1.py", "file2.py"])
    codebase_service_mock.read_file = AsyncMock(
        side_effect=[
            FileReadResult(file_path="file1.py", content="content1", status=FileStatus.SUCCESS),
            FileReadResult(file_path="file2.py", content="content2", status=FileStatus.SUCCESS),
        ]
    )

    # 2. Patch TreeContext
    tree_cls = mocker.patch("app.context.services.search.TreeContext")
    tree_instance = tree_cls.return_value
    tree_instance.grep.return_value = [1]
    tree_instance.format.return_value = "long content that exceeds limit"

    # Mock encoding to return length > limit.
    service.encoding = MagicMock()
    service.encoding.encode = MagicMock(return_value=[1] * 20)

    # 3. Execute
    result = await service.grep("pattern")

    # 4. Assert
    assert "truncated due to token limit" in result

    project_service_mock.get_active_project.assert_awaited_once_with()
    settings_service_mock.get_settings.assert_awaited_once_with()
    codebase_service_mock.resolve_file_patterns.assert_awaited_once_with("/tmp", None)
    assert codebase_service_mock.read_file.await_count == 1

async def test_grep_integration_patterns(service, temp_codebase, project_service_mock, codebase_service_mock, settings_service_mock, mocker):
    """
    Integration-style test using real TreeContext to verify regex pattern matching.
    """
    # 1. Setup
    project_service_mock.get_active_project = AsyncMock(return_value=Project(id=1, name="p", path="/tmp"))
    settings_service_mock.get_settings = AsyncMock(return_value=Settings(max_history_length=0, ast_token_limit=0, grep_token_limit=10000, diff_patches_auto_open=True, diff_patches_auto_apply=True, coding_llm_temperature=0.0))

    codebase_service_mock.resolve_file_patterns = AsyncMock(return_value=["src/grep_playground.py"])
    content = Path(temp_codebase.grep_playground).read_text(encoding="utf-8")
    codebase_service_mock.read_file = AsyncMock(return_value=FileReadResult(
        file_path="src/grep_playground.py", content=content, status=FileStatus.SUCCESS
    ))

    # We do NOT patch TreeContext here. We want to use the real one.
    # Ensure tiktoken encoding is mocked (already done in fixture)
    service.encoding = MagicMock()
    service.encoding.encode = MagicMock(return_value=[1])

    # 2. Test Regex Patterns

    # Case A: Simple String
    # grep_ast returns contextual blocks, so "Goodbye" can still appear as surrounding context.
    # We assert that the hello function is present.
    result = await service.grep("\\[ERROR\\]")
    assert "src/grep_playground.py:" in result
    assert "[ERROR] Something went wrong" in result


async def test_grep_integration_context_can_include_adjacent_function(
    service, project_service_mock, codebase_service_mock, settings_service_mock, mocker
):
    """Demonstrate TreeContext context behavior on a small file.

    When two functions are adjacent, searching for a match inside the first function can
    include the next function's definition as part of context.
    """
    project_service_mock.get_active_project = AsyncMock(return_value=Project(id=1, name="p", path="/tmp"))
    settings_service_mock.get_settings = AsyncMock(return_value=Settings(max_history_length=0, ast_token_limit=0, grep_token_limit=10000, diff_patches_auto_open=True, diff_patches_auto_apply=True, coding_llm_temperature=0.0))

    codebase_service_mock.resolve_file_patterns = AsyncMock(return_value=["test_file.py"])
    codebase_service_mock.read_file = AsyncMock(return_value=FileReadResult(
        file_path="test_file.py",
        content=(
            "def hello():\n"
            "    print('Hello World')\n\n"
            "def goodbye():\n"
            "    print('Goodbye World')\n"
        ),
        status=FileStatus.SUCCESS,
    ))

    service.encoding = MagicMock()
    service.encoding.encode = MagicMock(return_value=[1])

    result = await service.grep("Hello")
    assert "test_file.py:" in result
    assert "Hello World" in result
    assert "def goodbye():" in result


async def test_grep_integration_context_does_not_include_distant_function(
    service, temp_codebase, project_service_mock, codebase_service_mock, settings_service_mock, mocker
):
    """Demonstrate TreeContext context behavior on a larger file.

    TreeContext output includes AST-aware context; other scopes (like `omega`) can appear
    as context lines even when they do not match. Matches are marked with a "█" prefix,
    while non-matching context lines are prefixed with "│".
    """
    project_service_mock.get_active_project = AsyncMock(return_value=Project(id=1, name="p", path="/tmp"))
    settings_service_mock.get_settings = AsyncMock(return_value=Settings(max_history_length=0, ast_token_limit=0, grep_token_limit=10000, diff_patches_auto_open=True, diff_patches_auto_apply=True, coding_llm_temperature=0.0))

    codebase_service_mock.resolve_file_patterns = AsyncMock(return_value=["src/grep_playground.py"])
    codebase_service_mock.read_file = AsyncMock(return_value=FileReadResult(
        file_path="src/grep_playground.py",
        content=Path(temp_codebase.grep_playground).read_text(encoding="utf-8"),
        status=FileStatus.SUCCESS,
    ))

    service.encoding = MagicMock()
    service.encoding.encode = MagicMock(return_value=[1])

    result = await service.grep("\\[ERROR\\]")
    assert "src/grep_playground.py:" in result
    assert "[ERROR] Something went wrong" in result
    assert "█" in result
    assert "│def omega" in result
    assert "█def omega" not in result
    assert "█    msg = \"[ERROR] Something went wrong\"" in result

@pytest.mark.parametrize(
    ("pattern", "expected_substrings", "unexpected_substrings", "ignore_case"),
    [
        (r"def\s+my_func\(", ["def my_func("], [], True),
        (r"\[ERROR\]", ["[ERROR] Something went wrong"], [], True),
        (r"foo\.bar", ["foo.bar"], [], True),
        (r"foo.bar", ["foo.bar", "fooXbar"], [], True),
        (r"^def\s+my_func", ["def my_func("], [], True),
        (r"^pass", [], ["pass"], True),
        (r"^\s+pass$", ["pass"], [], True),
        (r"Users\\name", [r"Users\name"], [], True),
        (r"caf\u00e9", ["caf\u00e9"], [], True),
        (r"CAF\u00c9", ["caf\u00e9"], [], True),
        (r"(?<=foo\.)bar", ["foo.bar"], [], True),
        (r"(?i)\bclass\s+myclass\b", ["class MyClass:"], [], True),
    ],
)
async def test_grep_regex_complexity_real_tree_context(
    temp_codebase,
    mocker,
    project_service_mock,
    codebase_service_mock,
    settings_service_mock,
    pattern,
    expected_substrings,
    unexpected_substrings,
    ignore_case,
):
    """SearchService.grep should use real TreeContext and honor regex escaping/flags."""
    mocker.patch("tiktoken.get_encoding")
    service = SearchService(project_service_mock, codebase_service_mock, settings_service_mock)

    project_service_mock.get_active_project = AsyncMock(return_value=Project(id=1, name="p", path=temp_codebase.root))
    settings_service_mock.get_settings = AsyncMock(return_value=Settings(max_history_length=0, ast_token_limit=0, grep_token_limit=100_000, diff_patches_auto_open=True, diff_patches_auto_apply=True, coding_llm_temperature=0.0))

    # Use a .py file to avoid grep_ast "Unknown language" errors for .txt.
    # Use a larger playground file to make context inclusion stable.
    codebase_service_mock.resolve_file_patterns = AsyncMock(return_value=["src/grep_playground.py"])
    codebase_service_mock.read_file = AsyncMock(return_value=FileReadResult(
        file_path="src/grep_playground.py",
        content=Path(temp_codebase.grep_playground).read_text(encoding="utf-8"),
        status=FileStatus.SUCCESS,
    ))

    service.encoding = MagicMock()
    service.encoding.encode = MagicMock(return_value=[1])

    result = await service.grep(pattern, file_patterns=["src/grep_playground.py"], ignore_case=ignore_case)

    assert isinstance(result, str)
    for s in expected_substrings:
        assert s in result
    for s in unexpected_substrings:
        assert s not in result


async def test_grep_invalid_regex_best_effort_per_file(
    temp_codebase, mocker, project_service_mock, codebase_service_mock, settings_service_mock
):
    """Invalid regex should not hard-fail the request; it should report per-file error."""
    mocker.patch("tiktoken.get_encoding")
    service = SearchService(project_service_mock, codebase_service_mock, settings_service_mock)

    project_service_mock.get_active_project = AsyncMock(return_value=Project(id=1, name="p", path=temp_codebase.root))
    settings_service_mock.get_settings = AsyncMock(return_value=Settings(max_history_length=0, ast_token_limit=0, grep_token_limit=100_000, diff_patches_auto_open=True, diff_patches_auto_apply=True, coding_llm_temperature=0.0))
    codebase_service_mock.resolve_file_patterns = AsyncMock(return_value=["src/regex_cases.py"])
    codebase_service_mock.read_file = AsyncMock(return_value=FileReadResult(
        file_path="src/regex_cases.py",
        content=Path(temp_codebase.regex_file).read_text(encoding="utf-8"),
        status=FileStatus.SUCCESS,
    ))

    service.encoding = MagicMock()
    service.encoding.encode = MagicMock(return_value=[1])

    result = await service.grep(r"[unclosed", file_patterns=["src/regex_cases.py"])
    assert "Error processing" in result
    assert "regex_cases.py" in result


async def test_grep_skips_ignored_and_binary_via_read_file_status(
    mocker, project_service_mock, codebase_service_mock, settings_service_mock
):
    """Files that are not SUCCESS from CodebaseService.read_file must not be grepped."""
    mocker.patch("tiktoken.get_encoding")
    service = SearchService(project_service_mock, codebase_service_mock, settings_service_mock)

    project_service_mock.get_active_project = AsyncMock(return_value=Project(id=1, name="p", path="/tmp/project"))
    settings_service_mock.get_settings = AsyncMock(return_value=Settings(max_history_length=0, ast_token_limit=0, grep_token_limit=100_000, diff_patches_auto_open=True, diff_patches_auto_apply=True, coding_llm_temperature=0.0))

    codebase_service_mock.resolve_file_patterns = AsyncMock(return_value=["bin/data.bin", "logs/app.log"])
    codebase_service_mock.read_file.side_effect = [
        FileReadResult(file_path="bin/data.bin", content=None, status=FileStatus.BINARY),
        FileReadResult(file_path="logs/app.log", content=None, status=FileStatus.ERROR),
    ]

    result = await service.grep(r".", file_patterns=["bin/data.bin", "logs/app.log"])
    assert result == "No matches found."


async def test_grep_defaults_to_scan_all_pattern_when_file_patterns_none(
    mocker, temp_codebase, project_service_mock, codebase_service_mock, settings_service_mock
):
    """If file_patterns is None, SearchService delegates to resolve_file_patterns with None.

    CodebaseService.resolve_file_patterns will then apply SCAN_ALL_PATTERN=['.'].
    """
    mocker.patch("tiktoken.get_encoding")
    service = SearchService(project_service_mock, codebase_service_mock, settings_service_mock)

    project_service_mock.get_active_project = AsyncMock(return_value=Project(id=1, name="p", path=temp_codebase.root))
    settings_service_mock.get_settings = AsyncMock(return_value=Settings(max_history_length=0, ast_token_limit=0, grep_token_limit=100_000, diff_patches_auto_open=True, diff_patches_auto_apply=True, coding_llm_temperature=0.0))

    codebase_service_mock.resolve_file_patterns = AsyncMock(return_value=["src/main.py"])
    codebase_service_mock.read_file = AsyncMock(return_value=FileReadResult(
        file_path="src/main.py",
        content=Path(temp_codebase.main_py).read_text(encoding="utf-8"),
        status=FileStatus.SUCCESS,
    ))

    service.encoding = MagicMock()
    service.encoding.encode = MagicMock(return_value=[1])

    await service.grep("print")
    codebase_service_mock.resolve_file_patterns.assert_awaited_once_with(temp_codebase.root, None)


async def test_grep_unknown_language_reports_error_per_file(
    mocker, temp_codebase, project_service_mock, codebase_service_mock, settings_service_mock
):
    """Grep uses grep_ast.TreeContext which can error on unknown extensions (e.g. .txt).

    SearchService should catch and report this as an 'Error processing <file>: ...' entry.
    """
    mocker.patch("tiktoken.get_encoding")
    service = SearchService(project_service_mock, codebase_service_mock, settings_service_mock)

    project_service_mock.get_active_project = AsyncMock(return_value=Project(id=1, name="p", path=temp_codebase.root))
    settings_service_mock.get_settings = AsyncMock(return_value=Settings(max_history_length=0, ast_token_limit=0, grep_token_limit=100_000, diff_patches_auto_open=True, diff_patches_auto_apply=True, coding_llm_temperature=0.0))

    codebase_service_mock.resolve_file_patterns = AsyncMock(return_value=["src/regex_cases.txt"])
    codebase_service_mock.read_file = AsyncMock(return_value=FileReadResult(
        file_path="src/regex_cases.txt",
        content=Path(temp_codebase.regex_file).read_text(encoding="utf-8"),
        status=FileStatus.SUCCESS,
    ))

    service.encoding = MagicMock()
    service.encoding.encode = MagicMock(return_value=[1])

    result = await service.grep(r"\\[ERROR\\]")
    assert "Error processing src/regex_cases.txt:" in result
    assert "Unknown language" in result
