import logging
import os
from pathlib import Path

from app.context.models import ContextFile
from app.context.repositories import ContextRepository
from app.context.schemas import ContextFileCreate, ContextFileUpdate, FileReadResult, FileTreeNode
from app.context.services.codebase import CodebaseService
from app.projects.services import ProjectService
from app.projects.exceptions import ActiveProjectRequiredException

logger = logging.getLogger(__name__)


class WorkspaceService:
    def __init__(
        self,
        project_service: ProjectService,
        context_repo: ContextRepository,
        codebase_service: CodebaseService,
    ):
        self.project_service = project_service
        self.context_repo = context_repo
        self._codebase_service = codebase_service

    async def validate_file_access(self, file_path: str, must_exist: bool = True) -> Path:
        """
        Gatekeeper: Validates access to a file within the active project.
        Returns the absolute resolved path to the file.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required.")

        return await self._codebase_service.validate_file_path(project.path, file_path, must_exist=must_exist)

    async def add_file(self, session_id: int, file_path: str) -> ContextFile:
        """Promotes a file to the active context (Tier 2)."""
        # Gatekeeper check
        await self.validate_file_access(file_path, must_exist=True)

        existing = await self.context_repo.get_by_session_and_path(session_id, file_path)
        if existing:
            update_data = ContextFileUpdate(hit_count=existing.hit_count + 1)
            return await self.context_repo.update(db_obj=existing, obj_in=update_data)

        context_in = ContextFileCreate(session_id=session_id, file_path=file_path)
        return await self.context_repo.create(obj_in=context_in)

    async def remove_file(self, session_id: int, context_file_id: int) -> None:
        await self.context_repo.delete_by_session_and_id(session_id, context_file_id)

    async def delete_context_for_session(self, session_id: int) -> None:
        await self.context_repo.delete_all_by_session(session_id)

    async def get_active_context(self, session_id: int) -> list[ContextFile]:
        return await self.context_repo.list_by_session(session_id)

    async def add_context_files(self, session_id: int, files: list[str]) -> None:
        for file_path in files:
            try:
                await self.add_file(session_id, file_path)
            except ValueError:
                continue

    async def remove_context_files_by_path(self, session_id: int, files: list[str]) -> None:
        for file_path in files:
            await self.context_repo.delete_by_session_and_path(session_id, file_path)

    async def sync_files(self, session_id: int, filepaths: list[str]) -> None:
        """
        Smart Sync: Updates context to match the list, preserving metadata for existing files.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to sync context.")

        # 1. Delegate batch validation to CodebaseService
        # Returns a set of valid, absolute path strings
        valid_abs_paths = await self._codebase_service.filter_and_resolve_paths(project.path, filepaths)

        # 2. Convert to canonical relative paths for DB storage
        valid_incoming_paths = {os.path.relpath(p, project.path) for p in valid_abs_paths}

        # 3. Get current DB state
        current_context = await self.context_repo.list_by_session(session_id)
        current_paths = {c.file_path for c in current_context}

        # 4. Calculate Diff
        to_add = valid_incoming_paths - current_paths
        to_remove = current_paths - valid_incoming_paths

        # 5. Execute
        if to_remove:
            await self.remove_context_files_by_path(session_id, list(to_remove))
        if to_add:
            await self.add_context_files(session_id, list(to_add))

    async def get_active_file_paths_abs(self, session_id: int, project_root: str) -> list[str]:
        """
        Returns a list of absolute file paths for the active context.
        Filters out files that might have been ignored after they were added.
        """
        active_context_db = await self.get_active_context(session_id)
        active_abs_paths = []
        
        for item in active_context_db:
            if not await self._codebase_service.is_file_ignored(project_root, item.file_path):
                active_abs_paths.append(os.path.join(project_root, item.file_path))
                
        return active_abs_paths

    async def read_files_by_patterns(self, patterns: list[str]) -> list[FileReadResult]:
        """
        Reads files matching the given glob patterns within the active project.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to read files.")

        files = await self._codebase_service.resolve_file_patterns(project.path, patterns)
        return await self._codebase_service.read_files_content(project.path, files)

    async def read_files(self, file_paths: list[str]) -> list[FileReadResult]:
        """
        Reads specific files within the active project.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to read files.")
        return await self._codebase_service.read_files_content(project.path, file_paths)

    async def read_file(self, file_path: str) -> FileReadResult:
        """
        Reads a single file within the active project.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to read files.")
        return await self._codebase_service.read_file_content(project.path, file_path)

    async def get_project_file_tree(self) -> list[FileTreeNode]:
        """
        Builds the file tree for the active project.
        """
        project = await self.project_service.get_active_project()
        if not project:
            return []
        return await self._codebase_service.build_file_tree(project.path)

    async def scan_project_files(self, paths: list[str] | None = None) -> list[str]:
        """
        Scans the active project for files, respecting gitignore.
        Returns relative paths.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to scan files.")
        return await self._codebase_service.scan_files(project.path, paths)

    async def filter_and_resolve_paths(self, file_paths: list[str]) -> set[str]:
        """
        Filters a list of relative paths, removing ignored or unsafe files.
        Returns a set of absolute resolved paths.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to resolve files.")
        return await self._codebase_service.filter_and_resolve_paths(project.path, file_paths)

    async def save_file(self, file_path: str, content: str) -> None:
        """
        Writes a file to the active project workspace.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to save files.")
        
        await self._codebase_service.write_file(project.path, file_path, content)