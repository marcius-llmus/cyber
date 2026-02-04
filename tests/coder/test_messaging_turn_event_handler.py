"""Skeleton tests for coder MessagingTurnEventHandler.

Docstrings only; assertions/implementation added after skeleton approval.
"""


class TestMessagingTurnEventHandlerAgentStream:
    async def test_first_delta_yields_block_start_then_chunk(self):
        """First AgentStream delta should yield AIMessageBlockStartEvent then AIMessageChunkEvent."""
        pass

    async def test_subsequent_delta_same_block_yields_only_chunk(self):
        """When current text block exists, AgentStream delta yields only AIMessageChunkEvent."""
        pass


class TestMessagingTurnEventHandlerToolCall:
    async def test_tool_call_yields_agent_state_then_tool_call_event(self):
        """ToolCall should yield AgentStateEvent then ToolCallEvent."""
        pass

    async def test_tool_call_resets_text_block_so_next_stream_delta_starts_new_block(
        self,
    ):
        """After ToolCall, next AgentStream delta should create new block and yield AIMessageBlockStartEvent."""
        pass


class TestMessagingTurnEventHandlerToolCallResult:
    async def test_tool_call_result_updates_existing_tool_block_output(self):
        """ToolCallResult should update tool_call_data.output for matching internal_tool_call_id."""
        pass


class TestMessagingTurnEventHandlerUnknownEvents:
    async def test_unknown_event_type_yields_nothing(self):
        """Unknown event types should not raise; should yield nothing."""
        pass


class TestMessagingTurnEventHandlerStopAndCancel:
    async def test_stop_event_yields_nothing(self):
        """StopEvent should be handled gracefully and yield nothing."""
        pass

    async def test_workflow_cancelled_event_yields_nothing(self):
        """WorkflowCancelledEvent should be handled gracefully and yield nothing."""
        pass
