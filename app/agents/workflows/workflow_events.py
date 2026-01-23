from llama_index.core.tools import ToolOutput
from workflows.events import Event


class ToolCall(Event):
    """All tool calls are surfaced."""

    tool_name: str
    tool_kwargs: dict
    tool_id: str
    internal_tool_call_id: str


class ToolCallResult(Event):
    """Tool call result."""

    tool_name: str
    tool_kwargs: dict
    tool_id: str
    internal_tool_call_id: str
    tool_output: ToolOutput
    return_direct: bool
