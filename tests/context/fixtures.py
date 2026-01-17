from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.dependencies import get_context_page_service, get_context_service
from app.context.models import ContextFile
from app.context.repomap import RepoMap
from app.context.repositories import ContextRepository
from app.context.services import (
    CodebaseService,
    ContextPageService,
    FileSystemService,
    RepoMapService,
    SearchService,
    WorkspaceService,
)
from app.projects.services import ProjectService
from app.settings.services import SettingsService


@dataclass
class TempCodebase:
    root: str
    src_dir: str
    grep_playground: str
    readme: str
    main_py: str
    utils_py: str
    ignored_file: str
    ignored_dir: str
    binary_file: str
    binary_file_ignored: str
    outside_file: str
    glob_dir: str
    regex_file: str


@pytest.fixture
def temp_codebase(tmp_path):
    """Creates a temporary file structure for testing CodebaseService.
    Return a temporary directory path TempCodebase object which is unique to each test
    function invocation, created as a subdirectory of the base temporary
    directory.
    """

    # 1. Project Root
    project_root = tmp_path / "project"
    project_root.mkdir()

    # 2. Files inside project
    (project_root / ".gitignore").write_text("*.log\nignore_me.txt\nsecret/", encoding="utf-8")

    readme = project_root / "README.md"
    readme.write_text("# Test Project", encoding="utf-8")

    ignored_file = project_root / "ignore_me.txt"
    ignored_file.write_text("should be ignored", encoding="utf-8")

    # 3. Directories
    src_dir = project_root / "src"
    src_dir.mkdir()

    main_py = src_dir / "main.py"
    main_py.write_text("print('hello world')", encoding="utf-8")

    utils_py = src_dir / "utils.py"
    utils_py.write_text("def add(a, b): return a + b", encoding="utf-8")

    grep_playground = src_dir / "grep_playground.py"
    grep_playground.write_text(
        """\
\"\"\"Grep playground file.

This file is intentionally ~50 lines to make grep_ast.TreeContext context behavior
stable and realistic.
\"\"\"

from __future__ import annotations

import os
import re
from dataclasses import dataclass

API_KEY = \"sk-test_123\"
WINDOWS_PATH = r\"C:\\Users\\name\\file.txt\"


class MyClass:
    pass


def my_func(arg1: int, arg2: int) -> int:
    return arg1 + arg2


def alpha(value: int) -> str:
    \"\"\"Alpha function.

    Contains special chars and a literal dotted token.
    \"\"\"
    # Special chars: [](){}.*+?^$|\\
    msg = "[ERROR] Something went wrong"
    token = "foo.bar"
    return f"{msg} :: {token} :: {value}"


@dataclass
class Worker:
    name: str

    def run(self) -> None:
        # parentheses + braces below
        text = "(parentheses) and {braces}"
        _ = text

    def unicode(self) -> str:
        return "café"


def omega() -> str:
    \"\"\"Omega function far away.

    Contains a similar-but-not-equal token.
    \"\"\"
    token = "fooXbar"
    # Multiline markers:
    begin = "BEGIN"
    end = "END"
    return f"{token} {begin} {end}"
""",
        encoding="utf-8",
    )

    # Regex Playground File
    regex_content = (
        "def my_func(arg1, arg2):\n"
        "    return arg1 + arg2\n\n"
        "class MyClass:\n"
        "    pass\n\n"
        "# Special chars\n"
        "[ERROR] Something went wrong\n"
        "Path: C:\\Users\\name\\file.txt\n"
        "(parentheses)\n"
        "{braces}\n"
        "foo.bar\n"
        "fooXbar\n\n"
        "# Unicode\n"
        "café\n"
        "naïve\n\n"
        "# Multiline\n"
        "BEGIN\n"
        "content\n"
        "END\n"
    )
    # Keep .txt for CodebaseService reading tests, but also create a .py variant
    # because grep_ast TreeContext requires a known language (based on file extension).
    (src_dir / "regex_cases.txt").write_text(regex_content, encoding="utf-8")
    (src_dir / "regex_cases.py").write_text(regex_content, encoding="utf-8")

    # Glob Playground Directory
    glob_dir = src_dir / "glob_cases"
    glob_dir.mkdir()
    (glob_dir / "normal.txt").write_text("normal", encoding="utf-8")
    (glob_dir / "weird[name].txt").write_text("weird", encoding="utf-8")
    (glob_dir / ".hidden").write_text("hidden", encoding="utf-8")

    logs_dir = project_root / "logs"
    logs_dir.mkdir()
    (logs_dir / "app.log").write_text("error log", encoding="utf-8")

    secret_dir = project_root / "secret"
    secret_dir.mkdir()
    (secret_dir / "config.json").write_text("{}", encoding="utf-8")

    bin_dir = project_root / "bin"
    bin_dir.mkdir()

    binary_file = bin_dir / "data.bin"
    # Write invalid UTF-8 bytes to ensure it triggers binary detection
    binary_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x80\x81")

    binary_file_ignored = bin_dir / "image.png"
    binary_file_ignored.write_bytes(b"ignored binary")

    # 4. File outside project (for security tests)
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("hacker", encoding="utf-8")

    return TempCodebase(
        root=str(project_root),
        src_dir=str(src_dir),
        grep_playground=str(grep_playground),
        readme=str(readme),
        main_py=str(main_py),
        utils_py=str(utils_py),
        ignored_file=str(ignored_file),
        ignored_dir=str(secret_dir),
        binary_file=str(binary_file),
        binary_file_ignored=str(binary_file_ignored),
        outside_file=str(outside_file),
        glob_dir=str(glob_dir),
        regex_file=str(src_dir / "regex_cases.txt"),
    )


@pytest.fixture
def context_repository(db_session: AsyncSession) -> ContextRepository:
    return ContextRepository(db=db_session)


@pytest.fixture
def context_repository_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ContextRepository, instance=True)


@pytest.fixture
async def context_file(db_session: AsyncSession, chat_session) -> ContextFile:
    """DB-backed ContextFile fixture (repository tests only)."""
    obj = ContextFile(session_id=chat_session.id, file_path="src/main.py", hit_count=1)
    db_session.add(obj)
    await db_session.flush()
    await db_session.refresh(obj)
    return obj


@pytest.fixture
def project_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ProjectService, instance=True)


@pytest.fixture
def codebase_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(CodebaseService, instance=True)


@pytest.fixture
def workspace_service(
    project_service_mock: MagicMock,
    context_repository_mock: MagicMock,
    codebase_service_mock: MagicMock,
) -> WorkspaceService:
    return WorkspaceService(
        project_service=project_service_mock,
        context_repo=context_repository_mock,
        codebase_service=codebase_service_mock,
    )


@pytest.fixture
def workspace_service_mock(mocker: MockerFixture) -> MagicMock:
    service = mocker.create_autospec(WorkspaceService, instance=True)
    return service


@pytest.fixture
def file_system_service(
    project_service_mock: MagicMock,
    codebase_service_mock: MagicMock,
) -> FileSystemService:
    return FileSystemService(
        project_service=project_service_mock,
        codebase_service=codebase_service_mock,
    )


@pytest.fixture
def file_system_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(FileSystemService, instance=True)


@pytest.fixture
def search_service(
    project_service_mock: MagicMock,
    codebase_service_mock: MagicMock,
    settings_service_mock: MagicMock,
) -> SearchService:
    return SearchService(
        project_service=project_service_mock,
        codebase_service=codebase_service_mock,
        settings_service=settings_service_mock,
    )


@pytest.fixture
def search_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(SearchService, instance=True)


@pytest.fixture
def repomap_service(
    workspace_service_mock: MagicMock,
    project_service_mock: MagicMock,
    codebase_service_mock: MagicMock,
    settings_service_mock: MagicMock,
) -> RepoMapService:
    return RepoMapService(
        context_service=workspace_service_mock,
        codebase_service=codebase_service_mock,
        settings_service=settings_service_mock,
        project_service=project_service_mock,
    )


@pytest.fixture
def repomap_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(RepoMapService, instance=True)


@pytest.fixture
def settings_service_mock(mocker: MockerFixture) -> MagicMock:
    service = mocker.create_autospec(SettingsService, instance=True)
    service.get_settings = AsyncMock()
    return service


@pytest.fixture
def context_page_service(
    workspace_service_mock: MagicMock,
    file_system_service_mock: MagicMock,
    project_service_mock: MagicMock,
) -> ContextPageService:
    return ContextPageService(
        context_service=workspace_service_mock,
        fs_service=file_system_service_mock,
        project_service=project_service_mock,
    )


@pytest.fixture
def context_page_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ContextPageService, instance=True)


@pytest.fixture
def get_file_tree_page_data_mock() -> dict:
    return {
        "file_tree": {
            "type": "folder",
            "name": "root",
            "path": ".",
            "children": [
                {
                    "type": "folder",
                    "name": "src",
                    "path": "src",
                    "children": [
                        {
                            "type": "file",
                            "name": "main.py",
                            "path": "src/main.py",
                            "selected": True,
                        },
                    ],
                },
            ],
        }
    }


@pytest.fixture
def override_get_context_service(client, workspace_service_mock: MagicMock):
    client.app.dependency_overrides[get_context_service] = lambda: workspace_service_mock
    yield
    client.app.dependency_overrides.pop(get_context_service, None)


@pytest.fixture
def override_get_context_page_service(client, context_page_service_mock: MagicMock):
    client.app.dependency_overrides[get_context_page_service] = lambda: context_page_service_mock
    yield
    client.app.dependency_overrides.pop(get_context_page_service, None)


@pytest.fixture
def chat_session_mock(mocker: MockerFixture) -> MagicMock:
    """Unit-test safe ChatSession stand-in (no DB)."""
    obj = mocker.MagicMock()
    obj.id = 1
    return obj

@pytest.fixture
def repomap_tmp_project(tmp_path) -> dict:
    root = tmp_path / "project"
    root.mkdir()
    (root / "src").mkdir()

    # defs: core + class, plus a private def
    (root / "src" / "defs.py").write_text(
        """\
def core():
    return 1


def _hidden():
    return 2


class MyClass:
    def method(self):
        return core()
""",
        encoding="utf-8",
    )

    # usage
    (root / "src" / "use1.py").write_text(
        """\
from src.defs import core, MyClass


def run():
    core()
    x = MyClass()
    return x
""",
        encoding="utf-8",
    )
    (root / "src" / "use2.py").write_text(
        """\
from src.defs import core


def run2():
    core()
    core()
""",
        encoding="utf-8",
    )

    # separate definers to validate weighting differences
    (root / "src" / "public_defs.py").write_text(
        """\
def public():
    return 1
""",
        encoding="utf-8",
    )
    (root / "src" / "hidden_defs.py").write_text(
        """\
def _hidden2():
    return 2
""",
        encoding="utf-8",
    )
    (root / "src" / "refs_equal.py").write_text(
        """\
from src.public_defs import public
from src.hidden_defs import _hidden2


def run():
    public()
    _hidden2()
""",
        encoding="utf-8",
    )

    # unknown extension (should be ignored by extract_tags)
    (root / "notes.unknown").write_text("hello", encoding="utf-8")

    return {
        "root": str(root),
        "defs": str(root / "src" / "defs.py"),
        "use1": str(root / "src" / "use1.py"),
        "use2": str(root / "src" / "use2.py"),
        "public_defs": str(root / "src" / "public_defs.py"),
        "hidden_defs": str(root / "src" / "hidden_defs.py"),
        "refs_equal": str(root / "src" / "refs_equal.py"),
        "unknown": str(root / "notes.unknown"),
    }


@pytest.fixture
def repomap_instance(repomap_tmp_project) -> RepoMap:
    root = repomap_tmp_project["root"]
    all_files = [
        repomap_tmp_project["defs"],
        repomap_tmp_project["use1"],
        repomap_tmp_project["use2"],
        repomap_tmp_project["public_defs"],
        repomap_tmp_project["hidden_defs"],
        repomap_tmp_project["refs_equal"],
        repomap_tmp_project["unknown"],
    ]
    return RepoMap(
        all_files=all_files,
        active_context_files=[],
        mentioned_filenames=set(),
        mentioned_idents=set(),
        token_limit=10_000,
        root=root,
    )
