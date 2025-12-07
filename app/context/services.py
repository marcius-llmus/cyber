import os
import pathspec
import asyncio
import logging
import glob
import aiofiles
import aiofiles.os
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

    async def get_spec(self, project_root: str) -> pathspec.PathSpec:
        """Reads .gitignore and combines with default ignore patterns."""
        root = Path(project_root)
        gitignore_path = root / ".gitignore"
        lines = self.DEFAULT_PATTERNS[:]

        if await aiofiles.os.path.exists(gitignore_path):
            async with aiofiles.open(gitignore_path, "r") as f:
                content = await f.read()
                lines.extend(content.splitlines())

        return pathspec.PathSpec.from_lines(GitWildMatchPattern, lines)


class FileScanner:
    """Handles scanning the file system for files."""

    def __init__(self, matcher: IgnoreMatcher):
        self.matcher = matcher

    async def scan(self, project_root: str, paths: list[str] | None) -> list[str]:
        root = Path(project_root).resolve()
        spec = await self.matcher.get_spec(project_root)

        # Determine search roots: join project root with provided relative paths, or use project root
        if paths:
            search_roots = [root / p for p in paths]
        else:
            search_roots = [root]

        target_files = set()

        for item in search_roots:
            # Ensure item exists and is within root
            if not await aiofiles.os.path.exists(item):
                continue

            # Calculate relative path for matching
            try:
                rel_item = item.relative_to(root)
            except ValueError:
                # Path is not inside project root
                continue

            if await aiofiles.os.path.isfile(item):
                if not spec.match_file(str(rel_item)):
                    target_files.add(str(rel_item))
            elif await aiofiles.os.path.isdir(item):
                await self._scan_dir_recursive(item, root, spec, target_files)

        return sorted(list(target_files))

    async def _scan_dir_recursive(self, current_dir: Path, root: Path, spec: pathspec.PathSpec, target_files: set):
        try:
            entries = await aiofiles.os.listdir(current_dir)
        except OSError:
            return

        for entry in entries:
            full_path = current_dir / entry
            
            if await aiofiles.os.path.isdir(full_path):
                await self._scan_dir_recursive(full_path, root, spec, target_files)
            else:
                try:
                    rel_path = full_path.relative_to(root)
                    if not spec.match_file(str(rel_path)):
                        target_files.add(str(rel_path))
                except ValueError:
                    continue


class FileTreeBuilder:
    """Handles building the file tree structure."""

    def __init__(self, matcher: IgnoreMatcher):
        self.matcher = matcher

    async def build(self, project_root: str, active_files: set[str]) -> list[dict]:
        spec = await self.matcher.get_spec(project_root)

        async def _recurse(current_path: str) -> list[dict]:
            try:
                entries = sorted(await aiofiles.os.listdir(current_path))
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

                if await aiofiles.os.path.isdir(full_path):
                    children = await _recurse(full_path)
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

        return await _recurse(project_root)


class CodebaseService:
    """
    Service for interacting with the physical codebase (file system).
    Acts as a facade for file scanning and tree building operations.
    """

    def __init__(self):
        self.matcher = IgnoreMatcher()
        self.scanner = FileScanner(self.matcher)
        self.tree_builder = FileTreeBuilder(self.matcher)

    @staticmethod
    def _is_subpath(root: Path, path: Path) -> bool:
        """Checks if path is a subpath of root."""
        return path.resolve().is_relative_to(root.resolve())

    def is_safe_file(self, project_root: str | Path, file_path: str | Path) -> bool:
        """
        Verifies that the file path resolves to a location within the project root,
        exists, and is a file.
        """
        try:
            root = Path(project_root).resolve()
            path = Path(file_path)
            abs_path = path.resolve() if path.is_absolute() else (root / path).resolve()
            return self._is_subpath(root, abs_path) and abs_path.exists() and abs_path.is_file()
        except (OSError, ValueError):
            return False

    async def scan_files(self, project_root: str, paths: list[str] | None = None) -> list[str]:
        """
        Scans the project for files, respecting .gitignore.
        If paths is provided (relative to project root), scans those specific directories/files.
        Always returns relative paths from project root.
        Runs in a thread to avoid blocking the event loop.
        """
        return await self.scanner.scan(project_root, paths)

    async def build_file_tree(self, project_root: str, active_files: set[str]) -> list[dict]:
        """
        Asynchronously builds the file tree.
        active_files: A set of relative file paths that are currently in the context.
        """
        return await self.tree_builder.build(project_root, active_files)

    async def resolve_file_patterns(self, project_root: str, patterns: list[str]) -> list[str]:
        """
        Resolves a list of file paths or glob patterns to a list of existing relative file paths.
        Respects .gitignore via IgnoreMatcher.
        """
        spec = await self.matcher.get_spec(project_root)
        return await asyncio.to_thread(self._resolve_patterns_sync, project_root, patterns, spec)

    def _resolve_patterns_sync(self, project_root: str, patterns: list[str], spec: pathspec.PathSpec) -> list[str]:
        matched_files = set()
        root_path = Path(project_root).resolve()

        for pattern in patterns:
            full_pattern = os.path.join(project_root, pattern)
            found_paths = glob.glob(full_pattern, recursive=True)

            for path in found_paths:
                if os.path.isdir(path):
                    continue

                if not self._is_subpath(root_path, Path(path)):
                    continue
                
                rel_path = os.path.relpath(path, project_root)
                rel_path_str = str(Path(rel_path).as_posix())
                
                if not spec.match_file(rel_path_str):
                    matched_files.add(rel_path_str)
                    
        return sorted(list(matched_files))

    async def read_files_content(self, project_root: str, file_paths: list[str]) -> dict[str, str]:
        """
        Reads content of multiple files.
        Returns a dict of {file_path: content}.
        """
        results = {}
        root = Path(project_root).resolve()
        for file_path in file_paths:
            try:
                full_path = (root / file_path).resolve()
                if not self._is_subpath(root, full_path):
                    results[file_path] = "<error: access denied - path outside project root>"
                    continue

                async with aiofiles.open(str(full_path), "r", encoding="utf-8") as f:
                    results[file_path] = await f.read()
            except UnicodeDecodeError:
                results[file_path] = "<binary file>"
            except FileNotFoundError:
                results[file_path] = "<file not found>"
            except Exception as e:
                results[file_path] = f"<error reading file: {e}>"
        return results


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
                if self.codebase_service.is_safe_file(project.path, fp):
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
        return await repo_mapper.generate()