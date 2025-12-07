from app.context.schemas import FileReadResult, FileTreeNode
from app.context.services.codebase import CodebaseService
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.services import ProjectService


class FileSystemService:
    """
    Service responsible for Stateless I/O (Reading/Writing) within the Active Project.
    """
    def __init__(self, project_service: ProjectService, codebase_service: CodebaseService):
        self.project_service = project_service
        self.codebase_service = codebase_service

    # todo later should we centralize reading here? will we make CodebaseService internal?
    async def read_file(self, file_path: str) -> FileReadResult:
        """
        Reads a single file within the active project.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to read files.")
        
        return await self.codebase_service.read_file(project.path, file_path)

    async def read_files(self, file_patterns: list[str]) -> list[FileReadResult]:
        """
        Reads files matching the given glob patterns within the active project.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to read files.")

        files = await self.codebase_service.resolve_file_patterns(project.path, file_patterns)
        
        return await self.codebase_service.read_files(project.path, files)

    async def write_file(self, file_path: str, content: str) -> None:
        """
        Writes a file to the active project workspace.
        """
        project = await self.project_service.get_active_project()
        if not project:
            raise ActiveProjectRequiredException("Active project required to save files.")
        
        await self.codebase_service.write_file(project.path, file_path, content)

    async def get_project_file_tree(self) -> list[FileTreeNode]:
        """
        Builds the file tree for the active project.
        """
        project = await self.project_service.get_active_project()
        if not project:
            return []
        return await self.codebase_service.build_file_tree(project.path)