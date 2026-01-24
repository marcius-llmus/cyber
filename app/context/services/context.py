import logging
import os

from app.context.models import ContextFile
from app.context.repositories import ContextRepository
from app.context.schemas import ContextFileUpdate, ContextFileCreate
from app.context.services.codebase import CodebaseService
from app.patches.schemas import ParsedPatch
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.services import ProjectService

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
        self.codebase_service = codebase_service

    async def sync_context_for_diff(
        self, *, session_id: int, patch: ParsedPatch
    ) -> None:
        """Sync active context to reflect a single-file diff.

        Diff parsing belongs to the patches layer. This service operates on the parsed change.
        """

        if not (patch.is_added_file or patch.is_removed_file or patch.is_rename):
            return

        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required.")

        if patch.is_added_file or patch.is_rename:
            await self.add_file(session_id, patch.path)

        if patch.is_removed_file:
            await self.remove_context_files_by_path(session_id, [patch.path])

    async def add_file(self, session_id: int, file_path: str) -> ContextFile:
        """Promotes a file to the active context (Tier 2)."""
        # Gatekeeper check
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required.")

        # Validate existence via CodebaseService
        await self.codebase_service.validate_file_path(
            project.path, file_path, must_exist=True
        )

        existing = await self.context_repo.get_by_session_and_path(
            session_id, file_path
        )
        if existing:
            # todo: forgotten feature lol, hit count will affect file score in dynamic context
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

    async def remove_context_files_by_path(
        self, session_id: int, files: list[str]
    ) -> None:
        for file_path in files:
            await self.context_repo.delete_by_session_and_path(session_id, file_path)

    async def sync_files(self, session_id: int, filepaths: list[str]) -> None:
        """
        Smart Sync: Updates context to match the list, preserving metadata for existing files.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException(
                "Active project required to sync context."
            )

        valid_abs_paths = await self.codebase_service.filter_and_resolve_paths(
            project.path, filepaths
        )

        valid_incoming_paths = {
            os.path.relpath(p, project.path) for p in valid_abs_paths
        }

        current_context = await self.context_repo.list_by_session(session_id)
        current_paths = {c.file_path for c in current_context}

        to_add = valid_incoming_paths - current_paths
        to_remove = current_paths - valid_incoming_paths

        if to_remove:
            await self.remove_context_files_by_path(session_id, list(to_remove))
        if to_add:
            await self.add_context_files(session_id, list(to_add))

    async def get_active_file_paths_abs(
        self, session_id: int, project_root: str
    ) -> list[str]:
        """
        Returns a list of absolute file paths for the active context.
        Filters out files that might have been ignored after they were added.
        """
        active_context_db = await self.get_active_context(session_id)
        active_abs_paths = []

        for item in active_context_db:
            if not await self.codebase_service.is_ignored(project_root, item.file_path):
                active_abs_paths.append(os.path.join(project_root, item.file_path))

        return active_abs_paths