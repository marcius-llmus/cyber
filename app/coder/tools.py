from typing import Annotated

from pydantic import Field

from app.coder.constants import PATCHER_TOOL_DESCRIPTION
from app.coder.factories import build_patcher_service
from app.commons.tools import BaseToolSet


class PatcherTools(BaseToolSet):
    """Tools for applying code changes via Unified Diffs."""

    spec_functions = ["apply_diff"]

    async def apply_diff(
        self,
        file_path: Annotated[
            str, Field(description="The relative path of the file to modify (e.g., 'src/main.py').")
        ],
        diff: Annotated[str, Field(description=PATCHER_TOOL_DESCRIPTION)],
    ) -> str:
        """
        Applies a unified diff patch to a specific file.
        Use this tool when you need to edit code, add new files, or modify existing ones.
        """
        try:
            if not self.session_id:
                return "Error: No active session ID."

            async with self.db.session() as session:
                patcher = await build_patcher_service(session)
                return await patcher.apply_diff(file_path=file_path, diff_content=diff)

        except Exception as e:
            return f"Error applying patch: {str(e)}"
