"""Tests for coder MessagingTurnEventHandler.

Note: Recent combinations of `workflows` + `pydantic` can trigger a RecursionError
when accessing attributes on certain `workflows` Event subclasses created via
`model_construct()` (see failing stack traces involving workflows/events.py
`__getattr__`).

To keep these tests stable (and focused on our code), we avoid instantiating the
real `AgentStream` Pydantic model and instead exercise the underlying handler
with a minimal object exposing the `delta` attribute.
"""

from unittest.mock import AsyncMock

from llama_index.core.tools import ToolOutput
from workflows.events import StopEvent, WorkflowCancelledEvent

from app.agents.workflows.workflow_events import ToolCall, ToolCallResult
from app.coder.schemas import (
    AgentStateEvent,
    AIMessageBlockStartEvent,
    AIMessageChunkEvent,
    ToolCallEvent,
    ToolCallResultEvent,
    WorkflowLogEvent,
)


class TestMessagingTurnEventHandlerAgentStream:
    async def test_first_delta_yields_block_start_then_chunk(
        self, handler, fake_agent_stream_event
    ):
        """First AgentStream delta should yield AIMessageBlockStartEvent then AIMessageChunkEvent."""
        events = [
            e
            async for e in handler._handle_agent_stream_event(
                fake_agent_stream_event("Hello")
            )
        ]

        assert len(events) == 2
        assert isinstance(events[0], AIMessageBlockStartEvent)
        assert isinstance(events[1], AIMessageChunkEvent)
        assert events[1].delta == "Hello"
        assert events[0].block_id == events[1].block_id

    async def test_subsequent_delta_same_block_yields_only_chunk(
        self, handler, fake_agent_stream_event
    ):
        """When current text block exists, AgentStream delta yields only AIMessageChunkEvent."""
        # First call establishes block
        _ = [
            e
            async for e in handler._handle_agent_stream_event(
                fake_agent_stream_event("Hello")
            )
        ]

        # Second call
        events = [
            e
            async for e in handler._handle_agent_stream_event(
                fake_agent_stream_event(" World")
            )
        ]

        assert len(events) == 1
        assert isinstance(events[0], AIMessageChunkEvent)
        assert events[0].delta == " World"


class TestMessagingTurnEventHandlerToolCall:
    async def test_tool_call_yields_agent_state_then_tool_call_event(self, handler):
        """ToolCall should yield AgentStateEvent then ToolCallEvent."""
        event = ToolCall(
            tool_name="test_tool",
            tool_kwargs={},
            tool_id="id1",
            internal_tool_call_id="int_id1",
        )
        # Mock internal helper since it generates IDs
        handler._build_tool_call_event = AsyncMock(
            return_value=ToolCallEvent(
                tool_name="test_tool",
                tool_kwargs={},
                tool_id="id1",
                internal_tool_call_id="int_id1",
            )
        )

        events = [e async for e in handler.handle(event)]

        assert len(events) == 2
        assert isinstance(events[0], AgentStateEvent)
        assert isinstance(events[1], ToolCallEvent)

    async def test_tool_call_resets_text_block_so_next_stream_delta_starts_new_block(
        self, handler, fake_agent_stream_event
    ):
        """After ToolCall, next AgentStream delta should create new block and yield AIMessageBlockStartEvent."""
        # 1. Start text
        _ = [
            e
            async for e in handler._handle_agent_stream_event(
                fake_agent_stream_event("Hello")
            )
        ]
        initial_block_id = handler._accumulator.current_text_block_id

        # 2. Tool Call
        tc_event = ToolCall(
            tool_name="t",
            tool_kwargs={},
            tool_id="1",
            internal_tool_call_id="i1",
        )
        handler._build_tool_call_event = AsyncMock(
            return_value=ToolCallEvent(
                tool_name="t", tool_kwargs={}, tool_id="1", internal_tool_call_id="i1"
            )
        )
        async for _ in handler.handle(tc_event):
            pass

        # 3. Next text
        events = [
            e
            async for e in handler._handle_agent_stream_event(
                fake_agent_stream_event("Next")
            )
        ]

        assert isinstance(events[0], AIMessageBlockStartEvent)
        assert events[0].block_id != initial_block_id


class TestMessagingTurnEventHandlerToolCallResult:
    async def test_tool_call_result_updates_existing_tool_block_output(self, handler):
        """ToolCallResult should update tool_call_data.output for matching internal_tool_call_id."""
        # Setup accumulator with a tool call block
        handler._accumulator.blocks = [
            {
                "type": "tool",
                "internal_tool_call_id": "int_id1",
                "tool_call_data": {"output": None},
            }
        ]

        tool_output = ToolOutput(
            content="Output",
            tool_name="t",
            raw_input={},
            raw_output=None,
            is_error=False,
        )
        event = ToolCallResult(
            tool_name="t",
            tool_kwargs={},
            tool_id="id1",
            internal_tool_call_id="int_id1",
            tool_output=tool_output,
            return_direct=False,
        )

        events = [e async for e in handler.handle(event)]

        assert isinstance(events[0], ToolCallResultEvent)
        assert handler._accumulator.blocks[0]["tool_call_data"]["output"] == "Output"


class TestMessagingTurnEventHandlerUnknownEvents:
    async def test_unknown_event_type_yields_nothing(self, handler):
        """Unknown event types should not raise; should yield nothing."""

        class UnknownEvent:
            pass

        events = [e async for e in handler.handle(UnknownEvent())]
        assert len(events) == 0


class TestMessagingTurnEventHandlerStopAndCancel:
    async def test_stop_event_yields_nothing(self, handler):
        """StopEvent should be handled gracefully.

        Messaging layer yields AgentStateEvent(status="") to clear status line.
        """
        events = [e async for e in handler.handle(StopEvent())]
        assert len(events) == 1
        assert isinstance(events[0], AgentStateEvent)
        assert events[0].status == ""

    async def test_workflow_cancelled_event_yields_nothing(self, handler):
        """WorkflowCancelledEvent should be handled gracefully.

        Messaging layer yields a WorkflowLogEvent("Turn cancelled.") so UI logs show it.
        """
        events = [e async for e in handler.handle(WorkflowCancelledEvent())]
        assert len(events) == 1
        assert isinstance(events[0], WorkflowLogEvent)
        assert "cancelled" in events[0].message.lower()
