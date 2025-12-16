import logging
from typing import Any, AsyncGenerator, Callable

from llama_index.core.agent.workflow.workflow_events import (
    AgentInput,
    AgentOutput,
    AgentStream,
    ToolCall,
    ToolCallResult,
)

from app.chat.state import MessageStateAccumulator
from app.coder.schemas import (
    AIMessageBlockStartEvent,
    AIMessageChunkEvent,
    CoderEvent,
    WorkflowLogEvent,
    ToolCallEvent,
    ToolCallResultEvent,
    LogLevel,
    AgentStateEvent,
)

logger = logging.getLogger(__name__)


class TurnEventHandler:
    """
    Handles the translation of LlamaIndex events into CoderEvents for a specific turn.
    Holds the state (accumulator) for the duration of the stream.
    """
    def __init__(self, accumulator: MessageStateAccumulator):
        self.accumulator = accumulator
        self.handlers: dict[type, Callable[[Any], AsyncGenerator[CoderEvent, None]]] = {
            AgentStream: self._handle_agent_stream_event,
            ToolCall: self._handle_tool_call_event,
            ToolCallResult: self._handle_tool_call_result_event,
            AgentInput: self._handle_agent_input_event,
            AgentOutput: self._handle_agent_output_event,
        }

    async def handle(self, event: Any) -> AsyncGenerator[CoderEvent, None]:
        if not (handler := self.handlers.get(type(event))):
            logger.warning(f"No handler for event type: {type(event)}")
            return

        async for coder_event in handler(event):
            yield coder_event

    async def _handle_agent_stream_event(self, event: AgentStream) -> AsyncGenerator[CoderEvent, None]:
        if event.delta:
            prev_block_id = self.accumulator.current_text_block_id
            block_id = self.accumulator.append_text(event.delta)

            if prev_block_id != block_id:
                yield AIMessageBlockStartEvent(block_id=block_id)

            yield AIMessageChunkEvent(delta=event.delta, block_id=block_id)

        if event.tool_calls:
            yield AgentStateEvent(status=f"Calling {len(event.tool_calls)} tools...")

    async def _handle_tool_call_event(self, event: ToolCall) -> AsyncGenerator[CoderEvent, None]:
        yield AgentStateEvent(status=f"Calling tool `{event.tool_name}`...")
        
        tool_event = await self._build_tool_call_event(event)
        self.accumulator.add_tool_call(
            run_id=tool_event.tool_run_id,
            tool_id=tool_event.tool_id,
            name=tool_event.tool_name,
            kwargs=tool_event.tool_kwargs
        )
        yield tool_event

    async def _handle_tool_call_result_event(self, event: ToolCallResult) -> AsyncGenerator[CoderEvent, None]:
        result_event = await self._build_tool_call_result_event(event)
        self.accumulator.add_tool_result(run_id=result_event.tool_run_id, output=result_event.tool_output)
        yield result_event

    async def _handle_agent_input_event(self, event: AgentInput) -> AsyncGenerator[CoderEvent, None]: # noqa
        yield AgentStateEvent(status="Agent is planning next steps...")

    async def _handle_agent_output_event(self, event: AgentOutput) -> AsyncGenerator[CoderEvent, None]:
        content = ""
        if event.response and event.response.content:
            content = f" Output: {event.response.content[:50]}..."
        yield WorkflowLogEvent(message=f"Agent step completed.{content}", level=LogLevel.INFO)
        yield AgentStateEvent(status="")

    async def _build_tool_call_event(self, event: ToolCall) -> ToolCallEvent:
        unique_id = self._get_run_id(event.tool_kwargs, event.tool_name)
        return ToolCallEvent(
            tool_name=event.tool_name,
            tool_kwargs=event.tool_kwargs,
            tool_id=event.tool_id,
            tool_run_id=unique_id,
        )

    async def _build_tool_call_result_event(self, event: ToolCallResult) -> ToolCallResultEvent:
        content = str(event.tool_output.content)
        unique_id = self._get_run_id(event.tool_kwargs, event.tool_name)

        return ToolCallResultEvent(
            tool_name=event.tool_name,
            tool_output=content,
            tool_id=event.tool_id,
            tool_run_id=unique_id,
        )

    @staticmethod
    def _get_run_id(tool_kwargs: dict[str, Any], tool_name: str) -> str:
        if not (unique_id := tool_kwargs.get("_run_id")):
            raise ValueError(f"Run ID not found for tool {tool_name}")
        return unique_id