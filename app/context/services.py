import os
import pathspec
import asyncio
import logging
from pathlib import Path
from pathspec.patterns import GitWildMatchPattern
from app.settings.services import SettingsService

from app.context.models import ContextFile
from app.context.repositories import ContextRepository
from app.context.schemas import ContextFileCreate, ContextFileUpdate
from app.projects.services import ProjectService
from app.context.repomap import RepoMap
from app.projects.exceptions import ActiveProjectRequiredException

logger = logging.getLogger(__name__)


class IgnoreMatcher:
    """Handles gitignore pattern matching."""
    DEFAULT_PATTERNS = [
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

    def get_spec(self, project_root: str) -> pathspec.PathSpec:
        """Reads .gitignore and combines with default ignore patterns."""
        root = Path(project_root)
        gitignore_path = root / ".gitignore"
        lines = self.DEFAULT_PATTERNS[:]

        if gitignore_path.exists():
            with open(gitignore_path, "r") as f:
                lines.extend(f.read().splitlines())

        return pathspec.PathSpec.from_lines(GitWildMatchPattern, lines)


class FileScanner:
    """Handles scanning the file system for files."""

    def __init__(self, matcher: IgnoreMatcher):
        self.matcher = matcher

    def scan(self, project_root: str, paths: list[str] | None) -> list[str]:
        root = Path(project_root).resolve()
        spec = self.matcher.get_spec(project_root)

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


class FileTreeBuilder:
    """Handles building the file tree structure."""

    def __init__(self, matcher: IgnoreMatcher):
        self.matcher = matcher

    def build(self, project_root: str, active_files: set[str]) -> list[dict]:
        spec = self.matcher.get_spec(project_root)

        def _recurse(current_path: str) -> list[dict]:
            try:
                entries = sorted(os.listdir(current_path))
            except PermissionError:
                return []

            nodes = []
            for entry in entries:
                full_path = os.path.join(current_path, entry)
                rel_path = os.path.relpath(full_path, project_root)
                # Normalize to forward slashes for consistency
                rel_path_str = str(Path(rel_path).as_posix())

                if spec.match_file(rel_path_str):
                    continue

                if os.path.isdir(full_path):
                    children = _recurse(full_path)
                    if children:
                        nodes.append({
                            "type": "folder",
                            "name": entry,
                            "path": rel_path_str,
                            "children": children
                        })
                else:
                    nodes.append({
                        "type": "file",
                        "name": entry,
                        "path": rel_path_str,
                        "selected": rel_path_str in active_files
                    })

            # Sort folders first, then files
            return sorted(nodes, key=lambda x: (x["type"] == "file", x["name"].lower()))

        return _recurse(project_root)


class CodebaseService:
    """
    Service for interacting with the physical codebase (file system).
    Acts as a facade for file scanning and tree building operations.
    """

    def __init__(self):
        self.matcher = IgnoreMatcher()
        self.scanner = FileScanner(self.matcher)
        self.tree_builder = FileTreeBuilder(self.matcher)

    async def scan_files(self, project_root: str, paths: list[str] | None = None) -> list[str]:
        """
        Scans the project for files, respecting .gitignore.
        If paths is provided (relative to project root), scans those specific directories/files.
        Always returns relative paths from project root.
        Runs in a thread to avoid blocking the event loop.
        """
        return await asyncio.to_thread(self.scanner.scan, project_root, paths)

    async def build_file_tree(self, project_root: str, active_files: set[str]) -> list[dict]:
        """
        Asynchronously builds the file tree.
        active_files: A set of relative file paths that are currently in the context.
        """
        return await asyncio.to_thread(self.tree_builder.build, project_root, active_files)


class ContextService:
    def __init__(
        self,
        project_service: ProjectService,
        context_repo: ContextRepository,
        codebase_service: CodebaseService,
    ):
        self.project_service = project_service
        self.context_repo = context_repo
        self.codebase_service = codebase_service

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

    async def remove_file(self, session_id: int, context_file_id: int) -> None:
        """Removes a file from the active context by ID."""
        await self.context_repo.delete_by_session_and_id(session_id, context_file_id)

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

    async def remove_context_files_by_path(self, session_id: int, files: list[str]) -> None:
        """Batch removes files from the active context."""
        for file_path in files:
            await self.context_repo.delete_by_session_and_path(session_id, file_path)

    async def sync_files(self, session_id: int, filepaths: list[str]) -> None:
        """
        Replaces the current context with the provided list of files.
        This is used for the 'batch' update from the modal.
        """
        project = await self.project_service.get_active_project()
        if project:
            # Normalize and validate paths
            valid_paths = []
            for fp in filepaths:
                abs_path = os.path.join(project.path, fp)
                if os.path.exists(abs_path) and os.path.isfile(abs_path):
                    valid_paths.append(fp)
                else:
                    logger.warning(f"Ignored invalid or missing file path during sync: {fp}")
            filepaths = valid_paths

        # We wipe the existing context for this session and re-add the selected files.
        # A more optimized diff approach could be used, but for < 50 files, this is negligible.
        await self.context_repo.delete_all_by_session(session_id)
        await self.add_context_files(session_id, filepaths)

    async def get_file_tree_for_session(self, session_id: int) -> dict:
        project = await self.project_service.get_active_project()
        if not project:
            return {}

        active_context_files = await self.context_repo.list_by_session(session_id)
        active_paths = {f.file_path for f in active_context_files}

        children = await self.codebase_service.build_file_tree(project.path, active_paths)

        return {
            "type": "folder",
            "name": project.name,
            "path": ".",
            "children": children,
        }


class ContextPageService:
    def __init__(self, context_service: ContextService):
        self.context_service = context_service

    async def get_file_tree_page_data(self, session_id: int) -> dict:
        file_tree = await self.context_service.get_file_tree_for_session(session_id)
        return {"file_tree": file_tree}

    async def get_context_files_page_data(self, session_id: int) -> dict:
        files = await self.context_service.get_active_context(session_id)
        return {"files": files, "session_id": session_id}


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