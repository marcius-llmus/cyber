import os
from typing import Annotated

from pydantic import Field
from grep_ast import TreeContext
from app.core.db import DatabaseSessionManager
from app.settings.models import Settings
from app.commons.tools import BaseToolSet
from app.context.services import CodebaseService
from app.context.dependencies import build_context_service
from app.projects.exceptions import ActiveProjectRequiredException


class ContextTools(BaseToolSet):
    """Tools for managing the LLM's active context (reading/adding files)."""
    spec_functions = ["add_to_context", "remove_from_context"]

    async def add_to_context(
        self,
        files: Annotated[
            list[str],
            Field(
                description="List of relative file paths to load into the active context. Use this when you need to read the full content of files to understand or modify them."
            ),
        ],
    ) -> str:
        """
        Adds files to the active context.
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
        files: Annotated[
            list[str],
            Field(
                description="List of relative file paths to unload from the active context. Use this to free up token space when specific files are no longer needed for the current task."
            ),
        ],
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


class SearchTools(BaseToolSet):
    """Tools for high-level understanding via AST/Repo Maps (Tier 1)."""
    spec_functions = ["grep"]

    def __init__(
        self,
        db: DatabaseSessionManager,
        settings: Settings,
        codebase_service: CodebaseService,
        session_id: int | None = None,
    ):
        super().__init__(db, settings, session_id)
        self.codebase_service = codebase_service

    async def grep(
        self,
        pattern: Annotated[
            str,
            Field(
                description="The regular expression pattern to search for. Use this to find definitions, references, or specific code structures (e.g., 'class .*Service') across the codebase."
            ),
        ],
        paths: Annotated[
            list[str],
            Field(
                description="Optional list of specific file paths or directories to limit the search scope. If empty, the search is performed across the entire project."
            ),
        ] = None,
        ignore_case: Annotated[
            bool,
            Field(
                description="Set to True to perform a case-insensitive search. Defaults to True."
            ),
        ] = True,
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
