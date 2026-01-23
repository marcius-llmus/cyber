import inspect
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
)

from llama_index.core.tools import FunctionTool
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

    def __init__(
        self,
        fn: Optional[Callable[..., Any]] = None,
        metadata: Optional[ToolMetadata] = None,
        async_fn: Optional[AsyncCallable] = None,
        callback: Optional[Callable[..., Any]] = None,
        async_callback: Optional[Callable[..., Any]] = None,
        partial_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            fn=fn,
            metadata=metadata,
            async_fn=async_fn,
            callback=callback,
            async_callback=async_callback,
            partial_params=partial_params,
        )

        fn_to_inspect = fn or async_fn
        assert fn_to_inspect is not None
        sig = inspect.signature(fn_to_inspect)
        self.requires_internal_tool_call_id = any(
            _is_internal_tool_call_id_param(param) for param in sig.parameters.values()
        )
        self.internal_tool_call_id_param_name = (
            next(
                param.name
                for param in sig.parameters.values()
                if _is_internal_tool_call_id_param(param)
            )
            if self.requires_internal_tool_call_id
            else None
        )

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
