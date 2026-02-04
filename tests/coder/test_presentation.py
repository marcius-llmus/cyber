import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import WebSocketDisconnect

from app.coder.schemas import AIMessageChunkEvent, ToolCallEvent

class TestWebSocketOrchestrator:
    async def test_handle_connection_processes_messages(
        self,
        orchestrator,
        mock_websocket_manager,
        mock_coder_service,
        make_turn_execution,
    ):
        """handle_connection should read messages and invoke handle_user_message."""
        execution = make_turn_execution(
            items=[AIMessageChunkEvent(delta="Hi", block_id="b1")],
            user_message="Hello",
        )

        async def _handle_user_message(**kwargs):  # noqa: ANN001
            return execution

        mock_coder_service.handle_user_message = _handle_user_message

        await mock_websocket_manager.incoming.put(
            {"message": "Hello", "retry_turn_id": None}
        )
        await mock_websocket_manager.incoming.put(WebSocketDisconnect())
        
        # Act
        await orchestrator.handle_connection()
        
        assert execution.user_message == "Hello"

    async def test_handle_connection_handles_disconnect_gracefully(
        self,
        orchestrator,
        mock_websocket_manager,
        mock_coder_service,
        make_turn_execution,
        mocker,
    ):
        """WebSocketDisconnect should cancel the active run and exit."""
        execution = make_turn_execution(items=[AIMessageChunkEvent(delta="x", block_id="b")])
        # Orchestrator cancellation calls execution.cancel() -> handler.cancel_run().
        # In this unit test we bypass CoderService stream wiring, so we must provide
        # a handler stub explicitly.
        execution.handler = AsyncMock()
        execution.handler.cancel_run = AsyncMock()

        async def _stream_disconnect():
            raise WebSocketDisconnect()
            yield  # pragma: no cover

        execution.stream = _stream_disconnect()

        async def _handle_user_message(**kwargs):  # noqa: ANN001
            return execution

        mock_coder_service.handle_user_message = _handle_user_message

        await mock_websocket_manager.incoming.put(
            {"message": "Hello", "retry_turn_id": None}
        )
        await mock_websocket_manager.incoming.put(WebSocketDisconnect())

        await orchestrator.handle_connection()
        
        assert execution.handler.cancel_run.await_count == 1


    async def test_handle_connection_handles_cancellation_error(
        self,
        orchestrator,
        mock_websocket_manager,
        mock_coder_service,
        make_turn_execution,
        mocker,
    ):
        """asyncio.CancelledError should log cancellation and continue the loop."""
        execution = make_turn_execution(items=[])

        async def _stream_cancel():
            raise asyncio.CancelledError()
            yield  # pragma: no cover

        execution.stream = _stream_cancel()

        async def _handle_user_message(**kwargs):  # noqa: ANN001
            return execution

        mock_coder_service.handle_user_message = _handle_user_message

        await mock_websocket_manager.incoming.put({"message": "Msg1"})
        await mock_websocket_manager.incoming.put(WebSocketDisconnect())

        with patch("app.coder.presentation.logger") as mock_logger:
            await orchestrator.handle_connection()

            assert any(
                "Turn cancelled" in str(c) for c in mock_logger.info.call_args_list
            )


    async def test_handle_connection_continues_loop_after_cancellation(
        self,
        orchestrator,
        mock_websocket_manager,
        mock_coder_service,
        make_turn_execution,
    ):
        """After catching asyncio.CancelledError, the loop should continue processing next message."""
        exec1 = make_turn_execution(items=[])

        async def _cancel_stream():
            raise asyncio.CancelledError()
            yield  # pragma: no cover

        exec1.stream = _cancel_stream()

        exec2 = make_turn_execution(items=[])

        calls: list[dict] = []

        async def _handle_user_message(**kwargs):  # noqa: ANN001
            calls.append(kwargs)
            return exec1 if len(calls) == 1 else exec2

        mock_coder_service.handle_user_message = _handle_user_message

        await mock_websocket_manager.incoming.put({"message": "Msg1"})
        await mock_websocket_manager.incoming.put({"message": "Msg2"})
        await mock_websocket_manager.incoming.put(WebSocketDisconnect())

        await orchestrator.handle_connection()

        assert len(calls) == 2


    async def test_process_event_dispatches_to_correct_handler(self, orchestrator):
        """_process_event should look up the handler by event type and call it."""
        event = AIMessageChunkEvent(delta="hi", block_id="b1")
        turn = MagicMock()

        # _process_event dispatches via the event_handlers mapping, so ensure we patch the mapping.
        handler = AsyncMock()
        orchestrator.event_handlers[AIMessageChunkEvent] = handler
        
        await orchestrator._process_event(event, turn)
        
        handler.assert_awaited_once_with(event, turn=turn)


    async def test_render_tool_call_renders_diff_patch_if_apply_patch(self, orchestrator, mock_websocket_manager):
        """If tool name is 'apply_patch', it should attempt to render the diff patch view."""
        event = ToolCallEvent(tool_name="apply_patch", tool_kwargs={"patch": "diff"}, tool_id="t1", internal_tool_call_id="i1")
        turn = MagicMock()
        turn.settings_snapshot.diff_patch_processor_type = "codex"
        
        # Mock PatchRepresentation parsing
        with patch("app.coder.presentation.PatchRepresentation.from_text") as mock_parse:
            mock_patch = MagicMock()
            mock_patch.path = "file.py"
            mock_patch.diff = "diff"
            mock_patch.additions = 1
            mock_patch.deletions = 0
            mock_parse.return_value.patches = [mock_patch]
            
            await orchestrator._render_tool_call(event, turn)
            
            # Should send HTML for the tool item AND the diff patch
            assert len(mock_websocket_manager.sent_html) >= 2
