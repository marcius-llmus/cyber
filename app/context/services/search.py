import logging
import tiktoken
from grep_ast import TreeContext
from app.context.services.codebase import CodebaseService
from app.context.schemas import FileStatus
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.services import ProjectService
from app.settings.services import SettingsService

logger = logging.getLogger(__name__)

class SearchService:
    """
    Service responsible for Stateless Discovery (Grep, LS) within the Active Project.
    """
    def __init__(
        self, 
        project_service: ProjectService, 
        codebase_service: CodebaseService,
        settings_service: SettingsService
    ):
        self.project_service = project_service
        self.codebase_service = codebase_service
        self.settings_service = settings_service
        self.encoding = tiktoken.get_encoding("cl100k_base")

    async def grep(self, search_pattern: str | list[str], file_patterns: list[str] | None = None, ignore_case: bool = True) -> str:
        """
        Searches for a pattern in the active project.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to grep code.")
        
        settings = await self.settings_service.get_settings()
        token_limit = settings.grep_token_limit

        if isinstance(search_pattern, list):
            if not search_pattern:
                return "Error: Empty search pattern."
            search_pattern = "|".join(search_pattern)

        files = await self.codebase_service.resolve_file_patterns(project.path, file_patterns)
        output = []
        current_tokens = 0

        for file_path in files:
            result = await self.codebase_service.read_file(project.path, file_path)
            if result.status != FileStatus.SUCCESS:
                continue

            try:
                tc = TreeContext(result.file_path, result.content)
                loi = tc.grep(search_pattern, ignore_case=ignore_case)
                if loi:
                    tc.add_lines_of_interest(loi)
                    tc.add_context()
                    formatted_output = f"{result.file_path}:\n{tc.format()}"
                    tokens = len(self.encoding.encode(formatted_output))
                    
                    if current_tokens + tokens > token_limit:
                        logger.warning(f"Grep output truncated due to token limit ({token_limit}).")
                        output.append("... (grep output truncated due to token limit)")
                        break
                    
                    output.append(formatted_output)
                    current_tokens += tokens
            except Exception as e:
                output.append(f"Error processing {result.file_path}: {e}")

        return "\n\n".join(output) if output else "No matches found."