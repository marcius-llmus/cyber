import os
import logging
from typing import Annotated

from pydantic import Field
from app.core.db import DatabaseSessionManager
from app.settings.models import Settings
from app.commons.tools import BaseToolSet
from app.context.factories import build_filesystem_service, build_search_service
from app.context.schemas import FileStatus

logger = logging.getLogger(__name__)


class FileTools(BaseToolSet):
    """Tools for reading files from the codebase."""
    spec_functions = ["read_files"]

    async def read_files(
        self,
        file_patterns: Annotated[
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
                fs_service = await build_filesystem_service(session)
                results = await fs_service.read_files(file_patterns)
                
                if not results:
                    return "No files found matching the file patterns."

                output = []
                for result in results:
                    if result.status == FileStatus.SUCCESS:
                        output.append(f"## File: {result.file_path}\n{result.content}")
                    else:
                        output.append(f"## File: {result.file_path}\n[Error reading file: {result.status} - {result.error_message}]")
                
                return "\n\n".join(output)

        except Exception as e:
            return f"Error reading file: {str(e)}"


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
        search_pattern: Annotated[
            str,
            Field(
                description="The regular expression pattern to search for. Use this to find definitions, references, or specific code structures (e.g., 'class .*Service') across the codebase."
            ),
        ],
        file_patterns: Annotated[
            list[str],
            Field(
                description="Optional list of glob patterns (e.g., 'src/**/*.py', 'tests/*.ts') to limit the search scope. If empty, searches the entire project."
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
        try:
            async with self.db.session() as session:
                search_service = await build_search_service(session)
                return await search_service.grep(search_pattern, file_patterns, ignore_case)
        except Exception as e:
            return f"Error searching code: {str(e)}"