import logging
from typing import Annotated

from pydantic import Field
from app.core.db import DatabaseSessionManager
from app.settings.models import Settings
from app.commons.tools import BaseToolSet
from app.context.factories import build_filesystem_service, build_search_service
from app.context.schemas import FileStatus

logger = logging.getLogger(__name__)

FILE_PATTERNS_DESCRIPTION = """
List of specific file paths or glob patterns (e.g., 'src/**/*.py', 'tests/*.ts') to target.

USAGE GUIDELINES:
1. Specificity: Provide specific paths or narrow globs to limit scope and noise.
2. Multiple Patterns: Supports multiple patterns to target different areas simultaneously.
3. Exclusion: Do not include files that are already in the active context.
"""

GREP_PATTERN_DESCRIPTION = """
The regular expression pattern to search for.

USAGE GUIDELINES:
1. Specificity: Must be specific (e.g., 'class .*Service', 'def my_func'). Avoid broad patterns like '.*' or single common words.
2. Syntax: Supports standard Python regular expressions.
3. Context: The tool returns the AST context (surrounding code), so you don't need to match the whole block.
4. Format: Can be a single string or a list of strings (which will be joined with OR).
"""

GREP_IGNORE_CASE_DESCRIPTION = "Set to True to perform a case-insensitive search. Defaults to True."

LIST_FILES_PATH_DESCRIPTION = """
The relative path of the directory to list. Defaults to '.' (root).
"""


class FileTools(BaseToolSet):
    """Tools for reading files from the codebase."""
    spec_functions = ["read_files"] # "list_files"

    async def read_files(
        self,
        file_patterns: Annotated[
            list[str],
            Field(
                description=FILE_PATTERNS_DESCRIPTION
            ),
        ],
    ) -> str:
        """
        Reads the full content of files matching the provided patterns.

        USAGE:
        - Batching: Read ALL relevant files in a single tool call. Inefficiency is the enemy.
        - Context: Do NOT read files that are already in active context.
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
                description=LIST_FILES_PATH_DESCRIPTION
            ),
        ] = ".",
    ) -> str:
        """
        Lists files and directories in the given path.

        USAGE:
        - Purpose: Use this ONLY to explore directory structure when the Repository Map is insufficient.
        - Search: Do NOT use this to search for code. Use the `grep` tool for code discovery.
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
            str | list[str],
            Field(
                description=GREP_PATTERN_DESCRIPTION
            ),
        ],
        file_patterns: Annotated[
            list[str],
            Field(
                description=FILE_PATTERNS_DESCRIPTION
            ),
        ] = None,
        ignore_case: Annotated[
            bool,
            Field(
                description=GREP_IGNORE_CASE_DESCRIPTION
            ),
        ] = True,
    ) -> str:
        """
        Searches for a pattern in the specified files and returns the AST context 
        (surrounding classes/functions) for matches.

        EXPLORATION TOOL:
        Use this tool to locate code definitions (classes, functions) across the project.
        It provides AST-aware context, showing you the structure around matches.
        
        WORKFLOW:
        1. Search: Use `grep` to find where a symbol is defined or used.
        2. Locate: Identify the relevant file paths from the results.
        3. Read: Use `read_files` to examine the full content of those files.
        """
        try:
            async with self.db.session() as session:
                search_service = await build_search_service(session)
                return await search_service.grep(search_pattern, file_patterns, ignore_case)
        except Exception as e:
            logger.error(f"SearchTools.grep failed: {e}", exc_info=True)
            return f"Error searching code: {str(e)}"
