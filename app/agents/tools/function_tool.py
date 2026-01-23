import inspect
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
)

from llama_index.core.tools import FunctionTool
from llama_index.core.tools.function_tool import _is_context_param, sync_to_async, async_to_sync
from llama_index.core.tools.types import ToolMetadata, ToolOutput

from llamaindex_internals.base import AsyncCallable


def _is_internal_tool_call_id_param(param: inspect.Parameter) -> bool:
    """Check if a parameter is an injected internal tool call id."""
    return (param.name == "internal_tool_call_id") and (param.annotation == str)


class CustomFunctionTool(FunctionTool):
    """
    Function Tool.

    A tool that takes in a function, optionally handles workflow context,
    and allows the use of callbacks. The callback can return a new ToolOutput
    to override the default one or a string that will be used as the final content.
    """

    def call(self, *args: Any, **kwargs: Any) -> ToolOutput:
        """Sync Call."""
        all_kwargs = {**self.partial_params, **kwargs}
        if (
                self.requires_internal_tool_call_id
                and self.internal_tool_call_id_param_name is not None
        ):
            if self.internal_tool_call_id_param_name not in all_kwargs:
                raise ValueError("internal_tool_call_id is required for this tool")
        return super().call(**all_kwargs)


    async def acall(self, *args: Any, **kwargs: Any) -> ToolOutput:
        """Async Call."""
        all_kwargs = {**self.partial_params, **kwargs}
        if (
            self.requires_internal_tool_call_id
            and self.internal_tool_call_id_param_name is not None
        ):
            if self.internal_tool_call_id_param_name not in all_kwargs:
                raise ValueError("internal_tool_call_id is required for this tool")
        return await super().acall(**all_kwargs)
