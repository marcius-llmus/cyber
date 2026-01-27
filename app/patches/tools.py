import logging

from apply_patch_py.utils import (
    get_patch_format_instructions,
    get_patch_format_tool_instructions,
)
from llama_index.core.tools.types import ToolMetadata
from pydantic import BaseModel, Field, create_model

from app.commons.tools import BaseToolSet
from app.patches.enums import DiffPatchStatus, PatchProcessorType
from app.patches.factories import build_diff_patch_service
from app.patches.schemas import DiffPatchCreate

logger = logging.getLogger(__name__)

APPLY_UDIFF_PATCH_DESCRIPTION = """
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
APPLY_UDIFF_PATCH_TOOL_DESCRIPTION = "Apply a patch to the active project. Provide the patch text in the format described."

APPLY_CODEX_PATCH_DESCRIPTION = get_patch_format_instructions()
APPLY_CODEX_PATCH_TOOL_DESCRIPTION = get_patch_format_tool_instructions()


def _build_apply_patch_metadata(*, processor_type: PatchProcessorType) -> ToolMetadata:
    if processor_type == PatchProcessorType.CODEX_APPLY:
        patch_description = APPLY_CODEX_PATCH_DESCRIPTION
        tool_description = APPLY_CODEX_PATCH_TOOL_DESCRIPTION
    elif processor_type == PatchProcessorType.UDIFF_LLM:
        patch_description = APPLY_UDIFF_PATCH_DESCRIPTION
        tool_description = APPLY_UDIFF_PATCH_TOOL_DESCRIPTION
    else:
        raise RuntimeError("Invalid processor type")

    schema: type[BaseModel] = create_model(
        "ApplyPatchToolSchema",
        patch=(str, Field(description=patch_description)),
    )

    return ToolMetadata(
        name="apply_patch",
        description=tool_description,
        fn_schema=schema,
    )


class PatcherTools(BaseToolSet):
    """Tools for applying patch text to the active project."""

    spec_functions = ["apply_patch"]

    # NOTE: tool_run_id is UI-only. Diff patches are stored by (session_id, turn_id).

    @staticmethod
    def _format_save_result(
        *,
        patch_id: int,
        status: DiffPatchStatus,
        error_message: str | None,
    ) -> str:
        if status == DiffPatchStatus.APPLIED:
            return f"Applied patch (patch_id={patch_id})."
        if status == DiffPatchStatus.FAILED:
            return f"Failed to apply patch (patch_id={patch_id}): {error_message or 'Unknown error'}"
        if status == DiffPatchStatus.PENDING:
            return f"Patch saved (patch_id={patch_id}). Not applied (status=PENDING)."
        raise NotImplementedError(f"Unhandled DiffPatchStatus: {status} ")

    def to_tool_list(self, *args, **kwargs):
        processor_type = self.settings_snapshot.diff_patch_processor_type
        metadata = _build_apply_patch_metadata(processor_type=processor_type)
        return super().to_tool_list(
            *args, **kwargs, func_to_metadata_mapping={"apply_patch": metadata}
        )

    async def apply_patch(self, patch: str, internal_tool_call_id: str) -> str:
        try:
            if not self.session_id:
                raise RuntimeError("No active session_id available for patch tool")

            if not self.turn_id:
                raise RuntimeError("No active turn_id available for patch tool")

            processor_type = self.settings_snapshot.diff_patch_processor_type

            diff_patch_service = await build_diff_patch_service()
            payload = DiffPatchCreate(
                session_id=self.session_id,
                turn_id=self.turn_id,
                diff=patch,
                processor_type=processor_type,
            )
            result = await diff_patch_service.process_diff(payload)
            return self._format_save_result(
                patch_id=result.patch_id,
                status=result.status,
                error_message=result.error_message,
            )

        except Exception as e:
            logger.error(f"PatcherTools.apply_patch failed: {e}", exc_info=True)
            return f"Error saving/applying patch: {str(e)}"
