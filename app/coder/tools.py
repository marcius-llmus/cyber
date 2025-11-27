from typing import Annotated, List

from llama_index.core.tools import FunctionTool

from app.core.db import DatabaseSessionManager
from app.settings.models import Settings
from app.commons.tools import BaseToolSet
from app.context.services import CodebaseService
from app.context.dependencies import build_context_service
from app.projects.exceptions import ActiveProjectRequiredException

MAX_FILE_LIST_LENGTH = 10000  # Characters

class FileSystemTools(BaseToolSet):
    """Tools for spatial awareness and file discovery (Tier 0)."""

    def __init__(
        self,
        db: DatabaseSessionManager,
        settings: Settings,
        codebase_service: CodebaseService,
        session_id: int | None = None,
    ):
        super().__init__(db, settings, session_id)
        self.codebase_service = codebase_service

    @property
    def slug(self) -> str:
        return "filesystem"

    async def list_files(self) -> str:
        """
        Lists all files in the project, respecting .gitignore.
        Always starts from the project root to ensure safety.
        """
        async with self.db.session() as session:
            service = await build_context_service(session)
            project = await service.project_service.get_active_project()
            if not project:
                raise ActiveProjectRequiredException("Active project required to list files.")
            
            files = await self.codebase_service.scan_files(project_root=project.path)
            
        output = "\n".join(files)
        
        if len(output) > MAX_FILE_LIST_LENGTH:
            return output[:MAX_FILE_LIST_LENGTH] + f"\n\n... (List truncated, showing first {MAX_FILE_LIST_LENGTH} chars)"
            
        return output

    def get_tools(self) -> List[FunctionTool]:
        return [
            FunctionTool.from_defaults(async_fn=self.list_files, name="list_files"),
        ]


class ExecutionTools(BaseToolSet):
    """Tools for environment interaction and verification."""

    @property
    def slug(self) -> str:
        return "execution"

    def execute_command(
        self,
        command: Annotated[str, "The shell command to execute (e.g., 'pytest app/users')."],
    ) -> str:
        """
        Executes a shell command in a sandboxed environment.
        Use this to run tests, linters, or scripts.
        """
        return f"[Skeleton] Executing command: '{command}'."

    def get_tools(self) -> List[FunctionTool]:
        return [
            FunctionTool.from_defaults(fn=self.execute_command, name="execute_command"),
        ]