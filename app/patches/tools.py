import logging
from typing import Annotated

from pydantic import Field

from app.commons.tools import BaseToolSet
from app.patches.enums import DiffPatchStatus
from app.patches.factories import build_diff_patch_service
from app.patches.schemas import DiffPatchCreate

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

    # NOTE: tool_run_id is UI-only. Diff patches are stored by (session_id, turn_id).

    @staticmethod
    def _format_save_result(
        *,
        file_path: str,
        patch_id: int,
        status: DiffPatchStatus,
        error_message: str | None,
    ) -> str:
        if status == DiffPatchStatus.APPLIED:
            return f"Applied diff for {file_path} (patch_id={patch_id})."
        if status == DiffPatchStatus.FAILED:
            return f"Failed to apply diff for {file_path} (patch_id={patch_id}): {error_message or 'Unknown error'}"
        if status == DiffPatchStatus.PENDING:
            return f"Diff saved for {file_path} (patch_id={patch_id}). Not applied (status=PENDING)."
        raise NotImplementedError(f"Unhandled DiffPatchStatus: {status} ")

    async def apply_diff(
        self,
        file_path: Annotated[
            str, Field(description=FILE_PATH_DESCRIPTION)
        ],
        diff: Annotated[str, Field(description=APPLY_DIFF_DESCRIPTION)],
    ) -> str:
        """
        Submits a unified diff patch for a specific file.
        The patch is always saved; it may be auto-applied depending on settings.
        """
        try:
            if not self.session_id:
                raise RuntimeError("No active session_id available for patch tool")

            if not self.turn_id:
                raise RuntimeError("No active turn_id available for patch tool")

            diff_patch_service = await build_diff_patch_service()
            payload = DiffPatchCreate(
                session_id=self.session_id,
                turn_id=self.turn_id,
                diff=diff,
            )
            result = await diff_patch_service.process_diff(payload)
            return self._format_save_result(
                file_path=file_path,
                patch_id=result.patch_id,
                status=result.status,
                error_message=result.error_message,
            )

        except Exception as e:
            logger.error(f"PatcherTools.apply_diff failed: {e}", exc_info=True)
            return f"Error saving/applying patch: {str(e)}"
