from grep_ast import TreeContext
from app.context.services.codebase import CodebaseService
from app.context.schemas import FileStatus
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.services import ProjectService


class SearchService:
    """
    Service responsible for Stateless Discovery (Grep, LS) within the Active Project.
    """
    def __init__(self, project_service: ProjectService, codebase_service: CodebaseService):
        self.project_service = project_service
        self.codebase_service = codebase_service

    async def grep(self, search_pattern: str, file_patterns: list[str] | None = None, ignore_case: bool = True) -> str:
        """
        Searches for a pattern in the active project.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to grep code.")
        
        files = await self.codebase_service.resolve_file_patterns(project.path, file_patterns)
        output = []

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
                    output.append(f"{result.file_path}:\n{tc.format()}")
            except Exception as e:
                output.append(f"Error processing {result.file_path}: {e}")

        return "\n\n".join(output) if output else "No matches found."