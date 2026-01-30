import os

from app.context.repomap import RepoMap
from app.context.services.codebase import CodebaseService
from app.context.services.context import WorkspaceService
from app.core.enums import RepoMapMode
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.services import ProjectService


class RepoMapService:
    """
    Service for generating a context-aware map of the repository.
    """

    def __init__(
        self,
        context_service: WorkspaceService,
        codebase_service: CodebaseService,
        project_service: ProjectService,
    ):
        self.context_service = context_service
        self.codebase_service = codebase_service
        self.project_service = project_service

    @staticmethod
    def _parse_ignore_patterns(ignore_patterns_str: str | None) -> list[str]:
        return [
            p.strip() for p in (ignore_patterns_str or "").splitlines() if p.strip()
        ]

    # todo: refact mentioned filename and idents
    async def generate_repo_map(
        self,
        session_id: int,
        mentioned_filenames: set[str] | None = None,
        mentioned_idents: set[str] | None = None,
        include_active_content: bool = True,
        mode: RepoMapMode = RepoMapMode.AUTO,
        ignore_patterns_str: str | None = None,
        token_limit: int = 4096,
    ) -> str:
        """Generate a repository map string for the currently active project.

        The Repo Map is a Tier-1 context artifact meant to give the LLM a compact overview
        of the repository structure and (in AUTO mode) important definitions/references.

        Args:
            session_id: Session identifier used to fetch the active context files.
            mentioned_filenames: Optional set of project-relative paths mentioned by the
                user/agent. These are resolved and used as ranking boosts.
            mentioned_idents: Optional set of identifiers to boost during ranking.
            include_active_content: When True, includes full content of active context
                files in the output.
            mode: Controls how the map is generated:
                - TREE: only includes the file tree without any repomap definitions
                - AUTO: includes ranked definitions via Tree-sitter analysis.
                - MANUAL: returns only the top-level structure.
            ignore_patterns_str: Newline-separated gitignore-style patterns applied only
                during repo map generation.

                Important note about "ignore_patterns": it hides files/directories from
                the Repo Map output, but does not prevent the agent from accessing them
                through other mechanisms.

                Unlike hard exclusions (CodebaseService default ignore list) and the
                project's real .gitignore rules, these patterns do not make files
                inaccessible. They may still:
                - appear in the file/context tree UI,
                - be added to active context,
                - be searched/read explicitly by tools,
                as long as they are not blocked by the hard/default ignores or .gitignore.
            token_limit: Approximate token budget for the repo map output.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException(
                "Active project required to generate repo map."
            )

        ignore_patterns = self._parse_ignore_patterns(ignore_patterns_str)

        all_files_rel = await self.codebase_service.resolve_file_patterns(
            project.path,
            ignore_patterns=ignore_patterns,
        )
        all_files_abs = [os.path.join(project.path, f) for f in all_files_rel]

        active_files_abs = await self.context_service.get_active_file_paths_abs(
            session_id, project.path
        )

        if mentioned_filenames:
            mentioned_filenames = await self.codebase_service.filter_and_resolve_paths(
                project.path, list(mentioned_filenames)
            )
        else:
            mentioned_filenames = set()

        # todo: create a factory service for it (just like in agents)
        repo_mapper = RepoMap(
            all_files=all_files_abs,
            active_context_files=active_files_abs,
            mentioned_filenames=mentioned_filenames,
            mentioned_idents=mentioned_idents,
            token_limit=token_limit,
            root=project.path,
            include_definitions=(mode == RepoMapMode.AUTO),
        )

        if mode == RepoMapMode.MANUAL:
            return repo_mapper.format_top_level_structure()

        return await repo_mapper.generate(include_active_content=include_active_content)
