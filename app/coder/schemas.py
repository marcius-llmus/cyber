from enum import StrEnum
from typing import Any, TypeAlias, Union

from pydantic import BaseModel

from app.context.schemas import ContextFileListItem


class LogLevel(StrEnum):
    INFO = "info"
    ERROR = "error"


class WebSocketMessage(BaseModel):
    message: str
    retry_turn_id: str | None = None


class AIMessageChunkEvent(BaseModel):
    block_id: str
    delta: str


class AIMessageBlockStartEvent(BaseModel):
    block_id: str


class WorkflowErrorEvent(BaseModel):
    message: str
    original_message: str | None = None


class WorkflowLogEvent(BaseModel):
    message: str
    level: LogLevel = LogLevel.INFO


class UsageMetricsUpdatedEvent(BaseModel):
    session_cost: float
    monthly_cost: float
    input_tokens: int
    output_tokens: int
    cached_tokens: int


class ToolCallEvent(BaseModel):
    tool_name: str
    tool_kwargs: dict[str, Any]
    tool_id: str
    tool_run_id: str


class ToolCallResultEvent(BaseModel):
    tool_name: str
    tool_output: str
    tool_id: str
    tool_run_id: str


class SingleShotDiffAppliedEvent(BaseModel):
    file_path: str
    output: str


class AgentStateEvent(BaseModel):
    status: str


class ContextFilesUpdatedEvent(BaseModel):
    session_id: int
    files: list[ContextFileListItem]


CoderEvent: TypeAlias = Union[  # noqa
    AIMessageChunkEvent
    | AIMessageBlockStartEvent
    | WorkflowErrorEvent
    | WorkflowLogEvent
    | UsageMetricsUpdatedEvent
    | ToolCallEvent
    | ToolCallResultEvent
    | AgentStateEvent
    | SingleShotDiffAppliedEvent
    | ContextFilesUpdatedEvent
]
