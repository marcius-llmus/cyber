from enum import StrEnum

from pydantic import BaseModel
from typing import Union, Any


class LogLevel(StrEnum):
    INFO = "info"
    ERROR = "error"


class WebSocketMessage(BaseModel):
    message: str


class AIMessageChunkEvent(BaseModel):
    delta: str


class AIMessageCompletedEvent(BaseModel):
    message: str


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


class AgentStateEvent(BaseModel):
    status: str


CoderEvent = Union[
    AIMessageChunkEvent,
    AIMessageCompletedEvent,
    WorkflowErrorEvent,
    WorkflowLogEvent,
    UsageMetricsUpdatedEvent,
    ToolCallEvent,
    ToolCallResultEvent,
    AgentStateEvent,
]