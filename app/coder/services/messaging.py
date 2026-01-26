import logging
import uuid
from collections.abc import AsyncGenerator, Callable
from typing import Any

from llama_index.core.agent.workflow.workflow_events import (
    AgentInput,
    AgentOutput,
    AgentStream,
)

from app.agents.workflows.workflow_events import ToolCall, ToolCallResult
from app.coder.schemas import (
    AgentStateEvent,
    AIMessageBlockStartEvent,
    AIMessageChunkEvent,
    CoderEvent,
    LogLevel,
    ToolCallEvent,
    ToolCallResultEvent,
    WorkflowLogEvent,
)

logger = logging.getLogger(__name__)


class _MessageStateAccumulator:
    """
    Encapsulates the in-memory state of a message being generated.
    This mirrors the 'blocks' and 'tool_calls' columns in the DB.
    """

    def __init__(self):
        self.blocks: list[dict[str, Any]] = []
        self.current_text_block_id: str | None = None

    # we expect that a delta will always be related to its previous text block
    # a tool call represent the end of a text block
    def append_text(self, delta: str) -> str:
        """Appends text, creating a new block if necessary. Returns block_id."""
        if self.current_text_block_id is None:
            self.current_text_block_id = str(uuid.uuid4())
            self.blocks.append(
                {"type": "text", "block_id": self.current_text_block_id, "content": ""}
            )

        # Append to the last block (assuming it matches current ID)
        self.blocks[-1]["content"] += delta

        return self.current_text_block_id

    def add_tool_call(
        self, internal_tool_call_id: str, tool_id: str, name: str, kwargs: dict
    ):
        self.current_text_block_id = None  # Reset text block on tool call
        self.blocks.append(
            {
                "type": "tool",
                "internal_tool_call_id": internal_tool_call_id,
                "tool_name": name,
                "tool_call_data": {
                    "id": tool_id,
                    "name": name,
                    "kwargs": kwargs,
                    "output": None,
                },
            }
        )

    # Note for future devs: 'internal_tool_call_id' was intentionally added as this intruder argument lol
    # If "tool_id" (tool_call_id) was reliable from all llms, we would be able to use it nicely for correlation, but it
    # is not. Gemini for example  will not send it. That's why internal_tool_call_id is in block and not along with
    # its friends at tool_call_data. It does the job of "tool_id" but only for us. llm wrappers in theory should not
    # know it exists to not interfere with inner workings of "tool_id" required by many other llm providers.
    # todo not ideal, but for the small amount of items, it is ok
    def add_tool_result(self, internal_tool_call_id: str, output: str):
        for block in reversed(self.blocks):
            if (
                block.get("type") == "tool"
                and block.get("internal_tool_call_id") == internal_tool_call_id
            ):
                block["tool_call_data"]["output"] = output
                break

    def get_blocks(self) -> list[dict[str, Any]]:
        return self.blocks


class MessagingTurnEventHandler:
    """
    Handles the translation of LlamaIndex events into CoderEvents for a specific turn.
    Holds the state (accumulator) for the duration of the stream.
    """

    def __init__(self):
        self._accumulator = _MessageStateAccumulator()
        self.handlers: dict[type, Callable[[Any], AsyncGenerator[CoderEvent]]] = {
            AgentStream: self._handle_agent_stream_event,
            ToolCall: self._handle_tool_call_event,
            ToolCallResult: self._handle_tool_call_result_event,
            AgentInput: self._handle_agent_input_event,
            AgentOutput: self._handle_agent_output_event,
        }

    def get_blocks(self) -> list[dict[str, Any]]:
        return self._accumulator.get_blocks()

    async def handle(self, event: Any) -> AsyncGenerator[CoderEvent]:
        if not (handler := self.handlers.get(type(event))):
            logger.warning(f"No handler for event type: {type(event)}")
            return

        async for coder_event in handler(event):
            yield coder_event

    async def _handle_agent_stream_event(
        self, event: AgentStream
    ) -> AsyncGenerator[CoderEvent]:
        if event.delta:
            prev_block_id = self._accumulator.current_text_block_id
            block_id = self._accumulator.append_text(event.delta)

            if prev_block_id != block_id:
                yield AIMessageBlockStartEvent(block_id=block_id)

            yield AIMessageChunkEvent(delta=event.delta, block_id=block_id)

    async def _handle_tool_call_event(
        self, event: ToolCall
    ) -> AsyncGenerator[CoderEvent]:
        yield AgentStateEvent(status=f"Calling tool `{event.tool_name}`...")

        tool_event = await self._build_tool_call_event(event)
        self._accumulator.add_tool_call(
            internal_tool_call_id=tool_event.internal_tool_call_id,
            tool_id=tool_event.tool_id,
            name=tool_event.tool_name,
            kwargs=tool_event.tool_kwargs,
        )
        yield tool_event

    async def _handle_tool_call_result_event(
        self, event: ToolCallResult
    ) -> AsyncGenerator[CoderEvent]:
        result_event = await self._build_tool_call_result_event(event)
        self._accumulator.add_tool_result(
            internal_tool_call_id=result_event.internal_tool_call_id,
            output=result_event.tool_output,
        )
        yield result_event

    async def _handle_agent_input_event(
        self, event: AgentInput
    ) -> AsyncGenerator[CoderEvent, None]:  # noqa
        yield AgentStateEvent(status="Agent is planning next steps...")

    async def _handle_agent_output_event(
        self, event: AgentOutput
    ) -> AsyncGenerator[CoderEvent, None]:  # noqa
        content = ""
        if event.response and event.response.content:
            content = f" Output: {event.response.content[:50]}..."
        yield WorkflowLogEvent(
            message=f"Agent step completed.{content}", level=LogLevel.INFO
        )
        yield AgentStateEvent(status="")

    async def _build_tool_call_event(self, event: ToolCall) -> ToolCallEvent:
        internal_tool_call_id = event.internal_tool_call_id
        return ToolCallEvent(
            tool_name=event.tool_name,
            tool_kwargs=event.tool_kwargs,
            tool_id=event.tool_id,
            internal_tool_call_id=internal_tool_call_id,
        )

    async def _build_tool_call_result_event(
        self, event: ToolCallResult
    ) -> ToolCallResultEvent:
        content = str(event.tool_output.content)
        internal_tool_call_id = event.internal_tool_call_id

        return ToolCallResultEvent(
            tool_name=event.tool_name,
            tool_output=content,
            tool_id=event.tool_id,
            internal_tool_call_id=internal_tool_call_id,
        )
