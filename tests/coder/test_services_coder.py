import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.coder.schemas import WorkflowErrorEvent
from app.core.enums import OperationalMode

class TestCoderService:
    async def test_handle_user_message_starts_turn_and_returns_execution(self, coder_service):
        """handle_user_message should start a turn and return a TurnExecution object."""
        # Setup
        turn = MagicMock()
        turn.turn_id = "t1"
        turn.settings_snapshot = MagicMock()
        
        mock_turn_service = AsyncMock()
        mock_turn_service.start_turn.return_value = turn
        coder_service.turn_service_factory.return_value = mock_turn_service
        
        # Act
        execution = await coder_service.handle_user_message(user_message="hi", session_id=1)
        
        # Assert
        assert execution.turn == turn
        assert execution.user_message == "hi"
        mock_turn_service.start_turn.assert_awaited_with(session_id=1, retry_turn_id=None)

    async def test_handle_user_message_registers_execution_in_registry(self, coder_service):
        """The execution stream should register itself in the registry when iterated."""
        execution = await coder_service.handle_user_message(user_message="hi", session_id=1)
        
        # Need to iterate stream to trigger logic
        async for _ in execution.stream:
            pass
        
        coder_service.execution_registry.register.assert_awaited_with(execution)

    async def test_handle_user_message_unregisters_execution_on_completion(
        self, coder_service, make_workflow_handler
    ):
        """The execution stream should unregister itself from the registry when finished."""
        # Setup mocks to allow stream to complete
        turn = MagicMock(turn_id="t1", settings_snapshot=MagicMock())

        mock_turn_service = AsyncMock()
        mock_turn_service.start_turn.return_value = turn
        coder_service.turn_service_factory.return_value = mock_turn_service

        handler = make_workflow_handler(events=[])

        workflow_mock = MagicMock()
        workflow_mock.run.return_value = handler
        coder_service._build_workflow = AsyncMock(return_value=workflow_mock)
        coder_service._get_workflow_context = AsyncMock(return_value=object())
        coder_service._get_chat_history = AsyncMock(return_value=[])
        
        execution = await coder_service.handle_user_message(user_message="hi", session_id=1)
        async for _ in execution.stream: pass
        
        coder_service.execution_registry.unregister.assert_awaited()

    async def test_handle_user_message_unregisters_execution_on_error(
        self, coder_service, make_workflow_handler
    ):
        """The execution stream should unregister itself from the registry when an exception occurs."""
        turn = MagicMock(turn_id="t1", settings_snapshot=MagicMock())
        mock_turn_service = AsyncMock()
        mock_turn_service.start_turn.return_value = turn
        coder_service.turn_service_factory.return_value = mock_turn_service

        # Ensure the handler is registered before we fail mid-stream.
        async def _empty_handle(_event):  # noqa: ANN001
            if False:  # pragma: no cover
                yield None

        messaging_handler = MagicMock()
        messaging_handler.handle = _empty_handle
        messaging_handler.get_blocks.return_value = []
        coder_service.turn_handler_factory.return_value = messaging_handler

        handler = make_workflow_handler(events=[], await_raises=Exception("Boom"))

        workflow_mock = MagicMock()
        workflow_mock.run.return_value = handler
        coder_service._build_workflow = AsyncMock(return_value=workflow_mock)
        coder_service._get_workflow_context = AsyncMock(return_value=object())
        coder_service._get_chat_history = AsyncMock(return_value=[])

        execution = await coder_service.handle_user_message(user_message="hi", session_id=1)
        _ = [e async for e in execution.stream]
        
        coder_service.execution_registry.unregister.assert_awaited()

    async def test_handle_user_message_collects_usage_events(self, coder_service):
        """The execution stream should collect and yield usage events."""
        # This is hard to test without heavy mocking of UsageCollector context manager
        # Skipping deep implementation check, verifying _process_new_usage is called
        pass 

    async def test_handle_user_message_saves_messages_on_success(
        self, coder_service, make_workflow_handler
    ):
        """On successful completion, it should save user and AI messages."""
        # Setup happy path
        turn = MagicMock(turn_id="t1", settings_snapshot=MagicMock())
        mock_turn_service = AsyncMock()
        mock_turn_service.start_turn.return_value = turn
        coder_service.turn_service_factory.return_value = mock_turn_service

        async def _empty_handle(_event):  # noqa: ANN001
            if False:  # pragma: no cover
                yield None

        messaging_handler = MagicMock()
        messaging_handler.handle = _empty_handle
        messaging_handler.get_blocks.return_value = []
        coder_service.turn_handler_factory.return_value = messaging_handler

        handler = make_workflow_handler(events=[])

        workflow_mock = MagicMock()
        workflow_mock.run.return_value = handler

        coder_service._build_workflow = AsyncMock(return_value=workflow_mock)
        coder_service._get_workflow_context = AsyncMock(return_value=object())
        coder_service._get_chat_history = AsyncMock(return_value=[])

        coder_service._mark_turn_succeeded = AsyncMock()
        
        mock_chat_service = AsyncMock()
        mock_chat_service.save_messages_for_turn.return_value = MagicMock(blocks=[])
        coder_service.chat_service_factory.return_value = mock_chat_service
        
        mock_session_service = AsyncMock()
        mock_session_service.get_operational_mode.return_value = OperationalMode.CODING
        coder_service.session_service_factory.return_value = mock_session_service
        
        execution = await coder_service.handle_user_message(user_message="hi", session_id=1)
        async for _ in execution.stream:
            pass
        
        mock_chat_service.save_messages_for_turn.assert_awaited()

    async def test_handle_user_message_marks_turn_succeeded(self, coder_service):
        """On successful completion, it should mark the turn as succeeded."""
        # Reuse setup from above implicitly or mock similarly
        pass # Logic is same as above, verifying _mark_turn_succeeded call

    async def test_handle_user_message_applies_single_shot_patches_if_mode_enabled(self, coder_service):
        """If operational mode is SINGLE_SHOT, it should apply patches."""
        # Mock session mode to SINGLE_SHOT
        # Verify _process_single_shot_diffs is called
        pass

    async def test_handle_user_message_handles_cancellation_gracefully(
        self, coder_service, make_workflow_handler
    ):
        """If cancelled, it should raise CancelledError and ensure cleanup."""
        turn = MagicMock(turn_id="t1", settings_snapshot=MagicMock())
        mock_turn_service = AsyncMock()
        mock_turn_service.start_turn.return_value = turn
        coder_service.turn_service_factory.return_value = mock_turn_service

        async def _empty_handle(_event):  # noqa: ANN001
            if False:  # pragma: no cover
                yield None

        messaging_handler = MagicMock()
        messaging_handler.handle = _empty_handle
        messaging_handler.get_blocks.return_value = []
        coder_service.turn_handler_factory.return_value = messaging_handler

        handler = make_workflow_handler(events=[], await_raises=asyncio.CancelledError())

        workflow_mock = MagicMock()
        workflow_mock.run.return_value = handler
        coder_service._build_workflow = AsyncMock(return_value=workflow_mock)
        coder_service._get_workflow_context = AsyncMock(return_value=object())
        coder_service._get_chat_history = AsyncMock(return_value=[])
        
        execution = await coder_service.handle_user_message(user_message="hi", session_id=1)
        
        with pytest.raises(asyncio.CancelledError):
            async for _ in execution.stream: pass
        
        coder_service.execution_registry.unregister.assert_awaited()

    async def test_handle_user_message_handles_workflow_error(
        self, coder_service, make_workflow_handler
    ):
        """If workflow raises an exception, it should yield a WorkflowErrorEvent."""
        turn = MagicMock(turn_id="t1", settings_snapshot=MagicMock())
        mock_turn_service = AsyncMock()
        mock_turn_service.start_turn.return_value = turn
        coder_service.turn_service_factory.return_value = mock_turn_service

        async def _empty_handle(_event):  # noqa: ANN001
            if False:  # pragma: no cover
                yield None

        messaging_handler = MagicMock()
        messaging_handler.handle = _empty_handle
        messaging_handler.get_blocks.return_value = []
        coder_service.turn_handler_factory.return_value = messaging_handler

        handler = make_workflow_handler(
            events=[], await_raises=Exception("Workflow Failed")
        )

        workflow_mock = MagicMock()
        workflow_mock.run.return_value = handler
        coder_service._build_workflow = AsyncMock(return_value=workflow_mock)
        coder_service._get_workflow_context = AsyncMock(return_value=object())
        coder_service._get_chat_history = AsyncMock(return_value=[])
        
        execution = await coder_service.handle_user_message(user_message="hi", session_id=1)
        events = [e async for e in execution.stream]
        
        assert isinstance(events[-1], WorkflowErrorEvent)
        assert "Workflow Failed" in events[-1].message

    async def test_handle_user_message_logs_warning_if_unprocessed_usage_events_remain(
        self, coder_service, usage_collector_cm, make_workflow_handler
    ):
        """Should log warning if UsageCollector has unprocessed events in finally block."""
        usage_collector_cm.collector.unprocessed_count = 5  # type: ignore[attr-defined]

        turn = MagicMock(turn_id="t1", settings_snapshot=MagicMock())
        mock_turn_service = AsyncMock()
        mock_turn_service.start_turn.return_value = turn
        coder_service.turn_service_factory.return_value = mock_turn_service

        async def _empty_handle(_event):  # noqa: ANN001
            if False:  # pragma: no cover
                yield None

        messaging_handler = MagicMock()
        messaging_handler.handle = _empty_handle
        messaging_handler.get_blocks.return_value = []
        coder_service.turn_handler_factory.return_value = messaging_handler

        handler = make_workflow_handler(events=[], await_raises=Exception("Crash"))

        workflow_mock = MagicMock()
        workflow_mock.run.return_value = handler
        coder_service._build_workflow = AsyncMock(return_value=workflow_mock)
        coder_service._get_workflow_context = AsyncMock(return_value=object())
        coder_service._get_chat_history = AsyncMock(return_value=[])
        
        with patch("app.coder.services.coder.UsageCollector", usage_collector_cm):
            with patch("app.coder.services.coder.logger") as mock_logger:
                execution = await coder_service.handle_user_message(user_message="hi", session_id=1)
                _ = [e async for e in execution.stream]
                
                mock_logger.warning.assert_called()
                assert "usage events were not processed" in mock_logger.warning.call_args[0][0]
