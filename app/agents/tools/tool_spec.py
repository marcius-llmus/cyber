"""Base tool spec class."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Union

from llama_index.core.tools.types import ToolMetadata

from app.agents.tools.function_tool import CustomFunctionTool
from llamaindex_internals.base import BaseToolSpec

AsyncCallable = Callable[..., Awaitable[Any]]


# TODO: deprecate the Tuple (there's no use for it)
SPEC_FUNCTION_TYPE = Union[str, tuple[str, str]]


class CustomBaseToolSpec(BaseToolSpec):
    """Base tool spec class."""
    def to_tool_list(
        self,
        spec_functions: list[SPEC_FUNCTION_TYPE] | None = None,
        func_to_metadata_mapping: dict[str, ToolMetadata] | None = None,
    ) -> list[CustomFunctionTool]:
        """Convert tool spec to list of tools."""
        spec_functions = spec_functions or self.spec_functions
        func_to_metadata_mapping = func_to_metadata_mapping or {}
        tool_list = []
        for func_spec in spec_functions:
            func_sync = None
            func_async = None
            if isinstance(func_spec, str):
                func = getattr(self, func_spec)
                if asyncio.iscoroutinefunction(func):
                    func_async = func
                else:
                    func_sync = func
                metadata = func_to_metadata_mapping.get(func_spec, None)
                if metadata is None:
                    metadata = self.get_metadata_from_fn_name(func_spec)
            elif isinstance(func_spec, tuple) and len(func_spec) == 2:
                func_sync = getattr(self, func_spec[0])
                func_async = getattr(self, func_spec[1])
                metadata = func_to_metadata_mapping.get(func_spec[0], None)
                if metadata is None:
                    metadata = func_to_metadata_mapping.get(func_spec[1], None)
                    if metadata is None:
                        metadata = self.get_metadata_from_fn_name(func_spec[0])
            else:
                raise ValueError(
                    "spec_functions must be of type: List[Union[str, Tuple[str, str]]]"
                )

            tool = CustomFunctionTool.from_defaults(
                fn=func_sync,
                async_fn=func_async,
                tool_metadata=metadata,
            )
            tool_list.append(tool)
        return tool_list
