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
List of specific file paths or glob patterns to target within the active project root.

These patterns select which files are read and/or searched. The implementation uses Python glob semantics
(recursive '**' supported) and always applies ignore filtering (default ignores + project's .gitignore contents).

GLOB SYNTAX (Python glob):
- '*' matches any sequence of characters within a path segment.
- '?' matches a single character within a path segment.
- '**' matches across directory boundaries (recursive).
  Examples:
  - 'app/**/*.py'  -> all Python files under app/ at any depth
  - 'src/**/utils.py' -> matches utils.py at any depth under src/ (/**/ pattern supported)
  - '**/*.py' -> all Python files in the project

DEFAULT / SCAN-ALL BEHAVIOR:
- If file_patterns is None or an empty list, the resolver scans the whole project using SCAN_ALL_PATTERN = ['.'].
  Practical meaning: omitting file_patterns (or passing []) means “search/read everything under the project root”.

DIRECTORY INPUTS:
- You may pass a directory path (e.g., 'src' or 'src/glob_cases'). The resolver expands it by collecting files
  inside that directory (not just returning the directory itself). This is used to target “everything under a folder”.

SECURITY: ROOT BOUNDARY ENFORCEMENT:
- Patterns must remain within the project root. Any pattern that targets paths outside the root is rejected.
  Example: '../outside.txt' raises an access-denied style error.

IGNORE FILTERING:
- Even if a glob matches a file, it will be excluded if it is ignored by:
  1) default ignore patterns (e.g., '*.log' and other common noise/binary patterns)
  2) the project's .gitignore rules
- Example: 'logs/*.log' is excluded when '*.log' is ignored.

GLOB ESCAPING / SPECIAL CHARACTERS:
- Glob treats '[...]' as a character class, not a literal '[' and ']'.
  If you need to match a literal filename containing '[' or ']', you must escape it.
  Example (literal filename): 'weird[name].txt'
  - This may not match literally: 'src/glob_cases/weird[name].txt'
  - Use escaped '[':          'src/glob_cases/weird[[]name].txt'

NOTES:
- Resolved file paths are project-relative (e.g., 'src/main.py'), and downstream read/grep operates on those paths.
- Exclusion: Do not include files that are already in the active context as parameters.
- Provide specific paths or narrow globs to limit scope and noise.
- Supports multiple patterns to target different areas simultaneously. Use it as needed.
"""

GREP_PATTERN_DESCRIPTION = """
The regular expression (regex) pattern to search for inside selected files.

This is a true regex search executed line-by-line using Python's 're' engine:
- Each line is tested independently with re.search(pattern, line, flags).
- Case sensitivity is controlled by 'ignore_case' (re.IGNORECASE when enabled).
- The pattern can be:
  - a single regex string, OR
  - a list[str], which is combined into a single regex by joining with OR ('|').

REGEX SYNTAX & ESCAPING:
- Metacharacters are active unless escaped. Escape when searching for literal text.
  Examples:
  - Literal brackets: r'\\[ERROR\\]' matches '[ERROR]'
  - Literal dot:      r'foo\\.bar' matches 'foo.bar'
    Unescaped 'foo.bar' also matches strings like 'fooXbar' because '.' means “any character”.
  - Literal backslash (Windows paths): r'Users\\\\name' matches 'Users\\name'

STRUCTURAL / PRECISE PATTERNS:
- Anchors and boundaries work as expected with Python re:
  - '^def\\s+my_func\\(' matches a function definition at the start of a line
  - '(?i)\\bclass\\s+myclass\\b' matches a class definition regardless of case
  - '^\\s+pass$' matches an indented line that is exactly 'pass'
  (These are validated against our dedicated ~50-line grep playground file.)

OUTPUT IS CONTEXTUAL (AST-aware excerpt):
- The grep output is NOT just the matching line. After matches are found, the tool produces a formatted excerpt
  via an AST-based context builder (grep_ast):
  - Matching lines (lines of interest) are marked with a leading '█'
  - Context-only lines are marked with a leading '│'
  - Omitted sections are marked with '⋮'
- Because context is included, unrelated code (including other function/class definitions) can appear in the output
  even if it did not match:
  - In a small file, adjacent 'def goodbye()' can appear when searching for 'Hello'.
  - In a larger file, 'def omega()' can appear as context while not being marked as a match.
  To identify what actually matched, look for the '█' lines.

FILE EXTENSION / LANGUAGE PARSING:
- Context rendering requires a supported language inferred from the filename extension.
- If a file has an unsupported/unknown extension (e.g., '.txt'), grep returns a per-file error line such as:
  'Error processing <file>: Unknown language for <file>'

ERROR HANDLING FOR INVALID REGEX:
- Invalid regex patterns do not crash the entire grep request.
  Instead, the output includes a per-file error message:
  'Error processing <file>: <regex error>'

DEFAULT FILE SELECTION WHEN file_patterns IS OMITTED:
- If file_patterns is not provided to grep (None), the implementation delegates to file resolution with None.
  The resolver’s default scan-all behavior (SCAN_ALL_PATTERN=['.']) applies.
  
NOTES:
- Must be specific Avoid broad patterns like '.*' or single common words without specifying file scopes.
- The tool returns the AST context (surrounding code), so you don't need to match the whole block.
- Format: Can be a single string or a list of strings (which will be joined with OR).
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
