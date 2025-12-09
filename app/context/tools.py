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
    spec_functions = ["read_files", "list_files"]

    async def read_files(
        self,
        file_patterns: Annotated[
            list[str],
            Field(
                description="List of specific file paths or narrow glob patterns to read (e.g., ['src/auth/service.py', 'tests/unit/*.py']). "
                "DO NOT read the entire repository ('.') or broad patterns ('**') unless absolutely necessary. "
                "Use the Repository Map or grep to locate specific files first."
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
            logger.error(f"FileTools.read_files failed: {e}", exc_info=True)
            return f"Error reading file: {str(e)}"

    async def list_files(
        self,
        dir_path: Annotated[
            str,
            Field(
                description="The relative path of the directory to list (e.g., 'src', '.'). "
                "Use this ONLY if you need to explore the directory structure and the Repository Map is insufficient or missing. "
                "Do not use this to search for code; use grep instead."
            ),
        ] = ".",
    ) -> str:
        """
        Lists files and directories in the given path.
        """
        try:
            if not self.session_id:
                return "Error: No active session ID."

            async with self.db.session() as session:
                fs_service = await build_filesystem_service(session)
                items = await fs_service.list_files(dir_path)
                return "\n".join(items) if items else "Directory is empty."

        except Exception as e:
            logger.error(f"FileTools.list_files failed: {e}", exc_info=True)
            return f"Error listing files: {str(e)}"


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
                description="The regular expression pattern to search for. Use it to explore the file. "
                "Be specific. Avoid generic terms that match thousands of lines. "
                "Use this to find definitions, references, or specific code structures (e.g., 'class .*Service')."
            ),
        ],
        file_patterns: Annotated[
            list[str],
            Field(
                description="Optional list of glob patterns (e.g., 'src/**/*.py', 'tests/*.ts') to limit the search scope. "
                "You MUST provide specific file patterns or directories if known. "
                "Only leave empty if you truly need to search the ENTIRE project, which is slow."
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
            logger.error(f"SearchTools.grep failed: {e}", exc_info=True)
            return f"Error searching code: {str(e)}"