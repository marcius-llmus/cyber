from enum import StrEnum

from pydantic import BaseModel
from typing import Union


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


CoderEvent = Union[
    AIMessageChunkEvent,
    AIMessageCompletedEvent,
    WorkflowErrorEvent,
    WorkflowLogEvent,
    UsageMetricsUpdatedEvent,
]
