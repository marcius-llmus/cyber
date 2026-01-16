from dataclasses import dataclass
from unittest.mock import MagicMock
import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock

from app.context.models import ContextFile
from app.context.repositories import ContextRepository
from app.context.services import WorkspaceService, CodebaseService, FileSystemService, ContextPageService
from app.context.dependencies import get_context_service, get_context_page_service
from app.projects.services import ProjectService
from app.settings.services import SettingsService


@dataclass
class TempCodebase:
    root: str
    src_dir: str
    readme: str
    main_py: str
    utils_py: str
    ignored_file: str
    ignored_dir: str
    binary_file: str
    binary_file_ignored: str
    outside_file: str


@pytest.fixture
def temp_codebase(tmp_path):
    """Creates a temporary file structure for testing CodebaseService."""
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
        readme=str(readme),
        main_py=str(main_py),
        utils_py=str(utils_py),
        ignored_file=str(ignored_file),
        ignored_dir=str(secret_dir),
        binary_file=str(binary_file),
        binary_file_ignored=str(binary_file_ignored),
        outside_file=str(outside_file),
    )


@pytest.fixture
def context_repository(db_session: AsyncSession) -> ContextRepository:
    return ContextRepository(db=db_session)


@pytest.fixture
def context_repository_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ContextRepository, instance=True)


@pytest.fixture
async def context_file(db_session: AsyncSession, chat_session) -> ContextFile:
    context_file = ContextFile(
        session_id=chat_session.id, file_path="src/main.py", hit_count=1
    )
    db_session.add(context_file)
    await db_session.flush()
    await db_session.refresh(context_file)
    return context_file


@pytest.fixture
def codebase_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(CodebaseService, instance=True)


@pytest.fixture
def project_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ProjectService, instance=True)


@pytest.fixture
def workspace_service_mock(mocker: MockerFixture) -> MagicMock:
    service = mocker.create_autospec(WorkspaceService, instance=True)
    service.project_service = mocker.create_autospec(ProjectService, instance=True)
    service.project_service.get_active_project = AsyncMock()
    return service


@pytest.fixture
def file_system_service_mock(mocker: MockerFixture) -> MagicMock:
    service = mocker.create_autospec(FileSystemService, instance=True)
    service.get_project_file_tree = AsyncMock()
    return service


@pytest.fixture
def settings_service_mock(mocker: MockerFixture) -> MagicMock:
    service = mocker.create_autospec(SettingsService, instance=True)
    service.get_settings = AsyncMock()
    return service


@pytest.fixture
def context_page_service_mock(mocker: MockerFixture) -> MagicMock:
    service = mocker.create_autospec(ContextPageService, instance=True)
    service.get_file_tree_page_data = AsyncMock()
    service.get_context_files_page_data = AsyncMock()
    return service


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
