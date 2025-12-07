import os
import logging
from typing import Annotated

from pydantic import Field
from grep_ast import TreeContext
from app.core.db import DatabaseSessionManager
from app.settings.models import Settings
from app.commons.tools import BaseToolSet
from app.context.factories import build_workspace_service
from app.projects.exceptions import ActiveProjectRequiredException
from app.context.schemas import FileStatus

logger = logging.getLogger(__name__)


class ContextTools(BaseToolSet):
    """Tools for managing the LLM's active context (reading/adding files)."""
    # spec_functions = ["add_to_context", "remove_from_context"]
    spec_functions = ["read_files"]

    async def read_files(
        self,
        patterns: Annotated[
            list[str],
            Field(
                description="List of file paths or glob patterns to read (e.g., ['src/*.py', 'README.md']). "
                "The tool will resolve globs and return the content of all matching files."
            ),
        ],
    ) -> str:
        """
        Reads the full content of files matching the provided patterns.
        """
        try:
            if not self.session_id:
                return "Error: No active session ID."

            async with self.db.session() as session:
                context_service = await build_workspace_service(session)
                
                # Centralized call: Service handles project check, pattern resolution, and reading
                contents = await context_service.read_files_by_patterns(patterns)
                
                if not contents:
                    return "No files found matching the patterns."

                output = []
                for result in contents:
                    if result.status == FileStatus.SUCCESS:
                        output.append(f"## File: {result.file_path}\n{result.content}")
                    else:
                        output.append(f"## File: {result.file_path}\n[Error reading file: {result.status} - {result.error_message}]")
                
                return "\n\n".join(output)

        except Exception as e:
            logger.error(f"ContextTools: Error in read_files: {e}", exc_info=True)
            return f"Error reading files: {str(e)}"

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
                service = await build_workspace_service(session)
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
                service = await build_workspace_service(session)
                await service.remove_context_files_by_path(self.session_id, files)

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
        session_id: int | None = None,
    ):
        super().__init__(db, settings, session_id)

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
            service = await build_workspace_service(session)
            # 1. Scan for target files (enforces Active Project check)
            target_files = await service.scan_project_files(paths)
            
            # 2. Read content safely via Service
            read_results = await service.read_files(target_files)

        output = []

        # Grep
        for result in read_results:
            try:
                if result.status != FileStatus.SUCCESS:
                    continue
                
                tc = TreeContext(result.file_path, result.content)
                loi = tc.grep(pattern, ignore_case=ignore_case)
                
                if loi:
                    tc.add_lines_of_interest(loi)
                    tc.add_context()
                    output.append(f"{result.file_path}:\n{tc.format()}")
            except Exception as e:
                output.append(f"Error processing {result.file_path}: {e}")

        return "\n\n".join(output) if output else "No matches found."