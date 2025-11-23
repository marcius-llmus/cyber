from typing import Annotated, List

from llama_index.core.tools import FunctionTool
from app.commons.tools import BaseToolSet
from app.context.factories import context_service_factory
from app.context.exceptions import ContextException


class ContextTools(BaseToolSet):
    """Tools for managing the LLM's active context (reading/adding files)."""

    @property
    def slug(self) -> str:
        return "context"

    async def add_file(
        self,
        file_path: Annotated[
            str, "The full path of the file to add to context (e.g., 'app/main.py')"
        ],
    ) -> str:
        """
        Adds a specific file to the active context (Tier 2 memory).
        Use this when you need to read or edit a file's full content.
        """
        try:
            async with self.db.session() as session:
                service = await context_service_factory(session)
                await service.add_to_active_context(file_path)

            return f"File '{file_path}' successfully added to context."
        except ContextException as e:
            return f"Context Error: {str(e)}"
        except Exception as e:
            return f"System Error: {str(e)}"

    def get_tools(self) -> List[FunctionTool]:
        return [
            FunctionTool.from_defaults(async_fn=self.add_file, name="add_file_to_context"),
        ]
