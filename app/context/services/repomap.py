import os
from app.context.services.context import WorkspaceService
from app.context.services.codebase import CodebaseService
from app.settings.services import SettingsService
from app.projects.exceptions import ActiveProjectRequiredException
from app.context.repomap import RepoMap

class RepoMapService:
    """
    Service for generating a context-aware map of the repository.
    """

    def __init__(
        self,
        context_service: WorkspaceService,
        codebase_service: CodebaseService,
        settings_service: SettingsService,
    ):
        self.context_service = context_service
        self.codebase_service = codebase_service
        self.settings_service = settings_service

    async def generate_repo_map(
        self,
        session_id: int,
        mentioned_filenames: set[str] | None = None,
        mentioned_idents: set[str] | None = None,
    ) -> str:
        project = await self.context_service.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to generate repo map.")

        # Gather all files (Relative) -> Convert to Absolute for TreeSitter
        all_files_rel = await self.codebase_service.scan_files(project.path)
        all_files_abs = [os.path.join(project.path, f) for f in all_files_rel]

        active_files_abs = await self.context_service.get_active_file_paths_abs(session_id, project.path)

        if mentioned_filenames:
            mentioned_filenames = await self.codebase_service.filter_and_resolve_paths(project.path, list(mentioned_filenames))
        else:
            mentioned_filenames = set()

        settings = await self.settings_service.get_settings()

        repo_mapper = RepoMap(
            all_files=all_files_abs,
            active_context_files=active_files_abs,
            mentioned_filenames=mentioned_filenames,
            mentioned_idents=mentioned_idents,
            token_limit=settings.ast_token_limit,
            root=project.path,
        )
        return await repo_mapper.generate()