import os
from typing import Annotated, List

from grep_ast import TreeContext
from app.core.db import DatabaseSessionManager
from app.settings.models import Settings
from llama_index.core.tools import FunctionTool
from app.commons.tools import BaseToolSet
from app.context.services import CodebaseService
from app.context.dependencies import build_context_service
from app.projects.exceptions import ActiveProjectRequiredException


class ContextTools(BaseToolSet):
    """Tools for managing the LLM's active context (reading/adding files)."""

    @property
    def slug(self) -> str:
        return "context"

    async def add_to_context(
        self,
        files: Annotated[list[str], "List of file paths to read/add to context."],
    ) -> str:
        """
        Adds files to the active context (Tier 2 memory).
        Use this to read the full content of files you need to edit or understand deeply.
        """
        try:
            if not self.session_id:
                return "Error: No active session ID."

            async with self.db.session() as session:
                service = await build_context_service(session)
                await service.add_context_files(self.session_id, files)

            return f"Added {len(files)} files to context."
        except Exception as e:
            return f"Error adding files: {str(e)}"

    async def remove_from_context(
        self,
        files: Annotated[list[str], "List of file paths to remove from context."],
    ) -> str:
        """
        Removes files from the active context.
        Use this to free up token space when you are done with specific files.
        """
        try:
            if not self.session_id:
                return "Error: No active session ID."

            async with self.db.session() as session:
                service = await build_context_service(session)
                await service.remove_context_files(self.session_id, files)

            return f"Removed {len(files)} files from context."
        except Exception as e:
            return f"Error removing files: {str(e)}"

    async def view_context(self) -> str:
        """
        Lists the files currently loaded in the active context.
        """
        try:
            if not self.session_id:
                return "Error: No active session ID."

            async with self.db.session() as session:
                service = await build_context_service(session)
                context_files = await service.get_active_context(self.session_id)
                
                if not context_files:
                    return "Active context is empty."
                
                files_list = [f.file_path for f in context_files]
                return "Active Context Files:\n" + "\n".join(files_list)
        except Exception as e:
            return f"Error viewing context: {str(e)}"

    def get_tools(self) -> List[FunctionTool]:
        return [
            FunctionTool.from_defaults(async_fn=self.add_to_context, name="add_to_context"),
            FunctionTool.from_defaults(async_fn=self.remove_from_context, name="remove_from_context"),
            FunctionTool.from_defaults(async_fn=self.view_context, name="view_context"),
        ]


class SearchTools(BaseToolSet):
    """Tools for high-level understanding via AST/Repo Maps (Tier 1)."""

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
        return "search"

    async def grep(
        self,
        pattern: Annotated[str, "The regex pattern to search for (e.g., 'class .*Service')."],
        paths: Annotated[list[str], "Optional list of file paths to inspect. If empty, searches the whole project."] = [],
        ignore_case: Annotated[bool, "Whether to ignore case when searching."] = True,
    ) -> str:
        """
        Searches for a pattern in the specified files and returns the AST context 
        (surrounding classes/functions) for matches.
        """
        async with self.db.session() as session:
            service = await build_context_service(session)
            project = await service.project_service.get_active_project()
            if not project:
                raise ActiveProjectRequiredException("Active project required to grep code.")
            project_path = project.path

        target_files = await self.codebase_service.scan_files(project_root=project_path, paths=paths)

        output = []

        # Grep
        for file_path in target_files:
            try:
                full_path = os.path.join(project_path, file_path)
                with open(full_path, "r", encoding="utf-8") as f:
                    code = f.read()
                
                tc = TreeContext(file_path, code)
                loi = tc.grep(pattern, ignore_case=ignore_case)
                
                if loi:
                    tc.add_lines_of_interest(loi)
                    tc.add_context()
                    output.append(f"{file_path}:\n{tc.format()}")
            except Exception as e:
                output.append(f"Error processing {file_path}: {e}")

        return "\n\n".join(output) if output else "No matches found."

    def get_tools(self) -> List[FunctionTool]:
        return [
            FunctionTool.from_defaults(async_fn=self.grep, name="grep"),
        ]