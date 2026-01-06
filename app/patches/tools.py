import logging
from typing import Annotated

from pydantic import Field

from app.patches.factories import build_diff_patch_service
from app.commons.tools import BaseToolSet

logger = logging.getLogger(__name__)

APPLY_DIFF_DESCRIPTION = """
The changes to apply in Unified Diff format.

STRICT FORMAT RULES:
1. Format: Standard `diff -u` format.
   - Header: `--- source_file` and `+++ target_file`
   - Hunks: `@@ -start,count +start,count @@`
   - Context: MUST include 3-5 lines of UNCHANGED context before and after changes.
2. File Creation: Use `--- /dev/null` and `+++ path/to/new_file`.
3. File Deletion: Use `--- path/to/file` and `+++ /dev/null`.
4. No Markdown: Do NOT wrap the diff in markdown code blocks (```).

EXAMPLE:
--- app/main.py
+++ app/main.py
@@ -10,4 +10,4 @@
 def main():
-    print("Old")
+    print("New")
     return True
"""

FILE_PATH_DESCRIPTION = "The relative path of the file to modify (e.g., 'src/main.py')."


class PatcherTools(BaseToolSet):
    """Tools for applying code changes via Unified Diffs."""

    spec_functions = ["apply_diff"]

    @staticmethod
    def _format_apply_result(*, file_path: str, error_message: str | None) -> str:
        if error_message:
            return f"Error applying patch to {file_path}: {error_message}"
        return f"Successfully patched {file_path}"

    async def apply_diff(
        self,
        file_path: Annotated[
            str, Field(description=FILE_PATH_DESCRIPTION)
        ],
        diff: Annotated[str, Field(description=APPLY_DIFF_DESCRIPTION)],
    ) -> str:
        """
        Applies a unified diff patch to a specific file.
        Use this tool when you need to edit code, add new files, or modify existing ones.
        """
        try:
            if not self.session_id:
                return "Error: No active session ID."

            async with self.db.session() as session:
                diff_patch_service = await build_diff_patch_service(session)
                await diff_patch_service.apply_diff(file_path=file_path, diff_content=diff)
                return self._format_apply_result(file_path=file_path, error_message=None)

        except Exception as e:
            logger.error(f"PatcherTools.apply_diff failed: {e}", exc_info=True)
            return f"Error applying patch: {str(e)}"
