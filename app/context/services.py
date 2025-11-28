import os
import pathspec
import asyncio
from pathlib import Path
from pathspec.patterns import GitWildMatchPattern
from app.settings.services import SettingsService

from app.context.models import ContextFile
from app.context.repositories import ContextRepository
from app.context.schemas import ContextFileCreate, ContextFileUpdate
from app.projects.services import ProjectService
from app.context.repomap import RepoMap
from app.projects.exceptions import ActiveProjectRequiredException


class CodebaseService:
    """
    Service for interacting with the physical codebase (file system).
    Handles file discovery, gitignore rules, and reading content.
    """

    DEFAULT_IGNORE_PATTERNS = [
        ".aider*",
        ".git",
        # Common editor backup/temp files
        "*~",  # Emacs/vim backup
        "*.bak",  # Generic backup
        "*.swp",  # Vim swap
        "*.swo",  # Vim swap
        "\\#*\\#",  # Emacs auto-save
        ".#*",  # Emacs lock files
        "*.tmp",  # Generic temp files
        "*.temp",  # Generic temp files
        "*.orig",  # Merge conflict originals
        "*.pyc",  # Python bytecode
        "__pycache__/",  # Python cache dir
        ".DS_Store",  # macOS metadata
        "Thumbs.db",  # Windows thumbnail cache
        "*.svg",
        "*.pdf",
        # IDE files
        ".idea/",  # JetBrains IDEs
        ".vscode/",  # VS Code
        "*.sublime-*",  # Sublime Text
        ".project",  # Eclipse
        ".settings/",  # Eclipse
        "*.code-workspace",  # VS Code workspace
        # Environment files
        ".env",  # Environment variables
        ".venv/",  # Python virtual environments
        "node_modules/",  # Node.js dependencies
        "vendor/",  # Various dependencies
        # Logs and caches
        "*.log",  # Log files
        ".cache/",  # Cache directories
        ".pytest_cache/",  # Python test cache
        "coverage/",  # Code coverage reports
    ]

    async def scan_files(self, project_root: str, paths: list[str] | None = None) -> list[str]:
        """
        Scans the project for files, respecting .gitignore.
        If paths is provided (relative to project root), scans those specific directories/files.
        Always returns relative paths from project root.
        Runs in a thread to avoid blocking the event loop.
        """
        return await asyncio.to_thread(self._scan_files_sync, project_root, paths)

    def _scan_files_sync(self, project_root: str, paths: list[str] | None) -> list[str]:
        root = Path(project_root).resolve()
        gitignore_path = root / ".gitignore"
        
        ignore_lines = self.DEFAULT_IGNORE_PATTERNS[:]
        if gitignore_path.exists():
            with open(gitignore_path, "r") as f:
                ignore_lines.extend(f.readlines())
        
        spec = pathspec.PathSpec.from_lines(GitWildMatchPattern, ignore_lines)
        
        # Determine search roots: join project root with provided relative paths, or use project root
        if paths:
            search_roots = [root / p for p in paths]
        else:
            search_roots = [root]
            
        target_files = set()

        for item in search_roots:
            # Ensure item exists and is within root
            if not item.exists():
                continue
                
            # Calculate relative path for matching
            try:
                rel_item = item.relative_to(root)
            except ValueError:
                # Path is not inside project root
                continue

            if item.is_file():
                if not spec.match_file(str(rel_item)):
                    target_files.add(str(rel_item))
            elif item.is_dir():
                for dirpath, _, filenames in os.walk(item):
                    for filename in filenames:
                        file_path = Path(dirpath) / filename
                        try:
                            rel_path = file_path.relative_to(root)
                            if not spec.match_file(str(rel_path)):
                                target_files.add(str(rel_path))
                        except ValueError:
                            continue

        return sorted(list(target_files))


class ContextService:
    def __init__(self, project_service: ProjectService, context_repo: ContextRepository):
        self.project_service = project_service
        self.context_repo = context_repo

    async def add_file(self, session_id: int, file_path: str) -> ContextFile:
        """
        Promotes a file to the active context (Tier 2).
        If it already exists, increments hit_count and updates timestamp.
        """
        existing = await self.context_repo.get_by_session_and_path(session_id, file_path)
        if existing:
            update_data = ContextFileUpdate(hit_count=existing.hit_count + 1)
            return await self.context_repo.update(db_obj=existing, obj_in=update_data)

        context_in = ContextFileCreate(session_id=session_id, file_path=file_path)
        return await self.context_repo.create(obj_in=context_in)

    async def remove_file(self, session_id: int, file_path: str) -> None:
        """Removes a file from the active context."""
        await self.context_repo.delete_by_session_and_path(session_id, file_path)

    async def delete_context_for_session(self, session_id: int) -> None:
        """Deletes all context files associated with a session."""
        await self.context_repo.delete_all_by_session(session_id)

    async def get_active_context(self, session_id: int) -> list[ContextFile]:
        """Returns all files currently in the active context for this session."""
        return await self.context_repo.list_by_session(session_id)

    async def add_context_files(self, session_id: int, files: list[str]) -> None:
        """Batch adds files to the active context."""
        for file_path in files:
            await self.add_file(session_id, file_path)

    async def remove_context_files(self, session_id: int, files: list[str]) -> None:
        """Batch removes files from the active context."""
        for file_path in files:
            await self.remove_file(session_id, file_path)

    async def get_project_file_tree(self) -> dict:
        # This will be implemented to return the file structure for the UI
        active_project = await self.project_service.get_active_project()
        if not active_project:
            return {}

        return {
            "type": "folder",
            "name": active_project.name,
            "path": active_project.path,
            "children": [
                {
                    "type": "folder",
                    "name": "app",
                    "path": f"{active_project.path}/app",
                    "children": [
                        {"type": "file", "name": "main.py", "path": f"{active_project.path}/app/main.py"},
                        {"type": "file", "name": "models.py", "path": f"{active_project.path}/app/models.py"},
                    ],
                },
                {"type": "file", "name": "README.md", "path": f"{active_project.path}/README.md"},
            ],
        }


class ContextPageService:
    def __init__(self, context_service: ContextService):
        self.context_service = context_service

    async def get_file_tree_page_data(self) -> dict:
        file_tree = await self.context_service.get_project_file_tree()
        return {"file_tree": file_tree}


class RepoMapService:
    """
    Service for generating a context-aware map of the repository for the LLM.
    """

    def __init__(
        self,
        codebase_service: CodebaseService,
        context_service: ContextService,
        settings_service: SettingsService,
    ):
        self.codebase_service = codebase_service
        self.context_service = context_service
        self.settings_service = settings_service

    async def generate_repo_map(
        self,
        session_id: int,
        mentioned_filenames: set[str] | None = None,
        mentioned_idents: set[str] | None = None,
    ) -> str:
        """Orchestrates the generation of the repository map."""
        project = await self.context_service.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to generate repo map.")

        # Scan returns relative paths, but RepoMap needs absolute paths for file reading
        all_files_rel = await self.codebase_service.scan_files(project.path)
        all_files_abs = [os.path.join(project.path, f) for f in all_files_rel]

        active_context_db = await self.context_service.get_active_context(session_id)
        # Active context files are stored as relative paths
        active_context_files_abs = [os.path.join(project.path, item.file_path) for item in active_context_db]

        if mentioned_filenames:
            mentioned_filenames = {os.path.join(project.path, f) for f in mentioned_filenames}

        settings = await self.settings_service.get_settings()

        repo_mapper = RepoMap(
            all_files=all_files_abs,
            active_context_files=active_context_files_abs,
            mentioned_filenames=mentioned_filenames,
            mentioned_idents=mentioned_idents,
            token_limit=settings.ast_token_limit,
            root=project.path,
        )
        return repo_mapper.generate()
