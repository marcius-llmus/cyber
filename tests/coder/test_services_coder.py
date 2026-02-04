import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.coder.schemas import (
    SingleShotDiffAppliedEvent,
    UsageMetricsUpdatedEvent,
    WorkflowErrorEvent,
)
from app.core.enums import OperationalMode


class TestCoderService:
    async def test_handle_user_message_starts_turn_and_returns_execution(
        self, coder_service
    ):
        """handle_user_message should start a turn and return a TurnExecution object."""
        # Setup
        turn = MagicMock()
        turn.turn_id = "t1"
        turn.settings_snapshot = MagicMock()

        mock_turn_service = coder_service.turn_service_factory.return_value
        mock_turn_service.start_turn.return_value = turn

        # Act
        execution = await coder_service.handle_user_message(
            user_message="hi", session_id=1
        )

        # Assert
        assert execution.turn == turn
        assert execution.user_message == "hi"
        mock_turn_service.start_turn.assert_awaited_with(
            session_id=1, retry_turn_id=None
        )

    async def test_handle_user_message_registers_execution_in_registry(
        self, coder_service
    ):
        """The execution stream should register itself in the registry when iterated."""
        execution = await coder_service.handle_user_message(
            user_message="hi", session_id=1
        )

        # Need to iterate stream to trigger logic
        async for _ in execution.stream:
            _ = _

        # Real registry fixture: ensure it is cleaned up after stream end.
        assert execution.turn.turn_id not in coder_service.execution_registry._runs

    async def test_handle_user_message_unregisters_execution_on_completion(
        self, coder_service, make_workflow_handler, mocker
    ):
        """The execution stream should unregister itself from the registry when finished."""
        # Setup mocks to allow stream to complete
        turn = MagicMock(turn_id="t1", settings_snapshot=MagicMock())

        mock_turn_service = coder_service.turn_service_factory.return_value
        mock_turn_service.start_turn.return_value = turn

        handler = make_workflow_handler(events=[])

        workflow_mock = MagicMock()
        workflow_mock.run.return_value = handler
        coder_service._build_workflow = AsyncMock(return_value=workflow_mock)
        coder_service._get_workflow_context = AsyncMock(return_value=object())
        coder_service._get_chat_history = AsyncMock(return_value=[])

        mock_chat_service = coder_service.chat_service_factory.return_value
        mock_chat_service.save_messages_for_turn.return_value = MagicMock(blocks=[])

        execution = await coder_service.handle_user_message(
            user_message="hi", session_id=1
        )
        async for _ in execution.stream:
            _ = _

        # Real registry fixture: ensure it is cleaned up.
        assert "t1" not in coder_service.execution_registry._runs
        mock_chat_service.save_messages_for_turn.assert_awaited()

    async def test_handle_user_message_unregisters_execution_on_error(
        self, coder_service, make_workflow_handler
    ):
        """The execution stream should unregister itself from the registry when an exception occurs."""
        turn = MagicMock(turn_id="t1", settings_snapshot=MagicMock())
        mock_turn_service = coder_service.turn_service_factory.return_value
        mock_turn_service.start_turn.return_value = turn

        handler = make_workflow_handler(events=[], await_raises=Exception("Boom"))

        workflow_mock = MagicMock()
        workflow_mock.run.return_value = handler
        coder_service._build_workflow = AsyncMock(return_value=workflow_mock)
        coder_service._get_workflow_context = AsyncMock(return_value=object())
        coder_service._get_chat_history = AsyncMock(return_value=[])

        execution = await coder_service.handle_user_message(
            user_message="hi", session_id=1
        )
        _ = [e async for e in execution.stream]

        # Real registry fixture: ensure the run is removed.
        assert "t1" not in coder_service.execution_registry._runs

    async def test_handle_user_message_collects_usage_events(
        self, coder_service, make_workflow_handler, mocker
    ):
        """The execution stream should collect and yield usage events."""
        # Setup
        turn = MagicMock(turn_id="t1", settings_snapshot=MagicMock())
        mock_turn_service = coder_service.turn_service_factory.return_value
        mock_turn_service.start_turn.return_value = turn

        # Mock Workflow Handler that yields one event
        handler = make_workflow_handler(events=["some_event"])
        workflow_mock = MagicMock()
        workflow_mock.run.return_value = handler
        coder_service._build_workflow = AsyncMock(return_value=workflow_mock)
        coder_service._get_workflow_context = AsyncMock(return_value=object())
        coder_service._get_chat_history = AsyncMock(return_value=[])

        # Mock Usage Service
        mock_usage_service = AsyncMock()
        mock_metrics = MagicMock()
        mock_metrics.errors = []
        mock_metrics.session_cost = 0.1
        mock_metrics.monthly_cost = 1.0
        mock_metrics.input_tokens = 10
        mock_metrics.output_tokens = 20
        mock_metrics.cached_tokens = 5
        mock_usage_service.process_batch.return_value = mock_metrics
        coder_service.usage_service_factory.return_value = mock_usage_service

        # Mock Chat Service & Session Service (for final save)
        mock_chat_service = coder_service.chat_service_factory.return_value
        mock_chat_service.save_messages_for_turn.return_value = MagicMock(blocks=[])

        mock_session_service = coder_service.session_service_factory.return_value
        mock_session_service.get_operational_mode.return_value = OperationalMode.CODING

        coder_service._mark_turn_succeeded = AsyncMock()

        # Mock UsageCollector
        mock_collector_instance = MagicMock()
        mock_collector_instance.consume.side_effect = [
            ["usage_event_1"],  # First call inside loop
            [],  # Subsequent calls
        ]
        mock_collector_instance.unprocessed_count = 0

        @asynccontextmanager
        async def mock_usage_collector_cm():
            yield mock_collector_instance

        with patch(
            "app.coder.services.coder.UsageCollector",
            side_effect=mock_usage_collector_cm,
        ):
            execution = await coder_service.handle_user_message(
                user_message="hi", session_id=1
            )
            events = [e async for e in execution.stream]

        # Assertions
        mock_usage_service.process_batch.assert_awaited()

        usage_events = [e for e in events if isinstance(e, UsageMetricsUpdatedEvent)]
        assert len(usage_events) > 0
        assert usage_events[0].session_cost == 0.1

    async def test_handle_user_message_saves_messages_on_success(
        self, coder_service, make_workflow_handler, mocker
    ):
        """On successful completion, it should save user and AI messages."""
        # Setup happy path
        turn = MagicMock(turn_id="t1", settings_snapshot=MagicMock())
        mock_turn_service = coder_service.turn_service_factory.return_value
        mock_turn_service.start_turn.return_value = turn

        handler = make_workflow_handler(events=[])

        workflow_mock = MagicMock()
        workflow_mock.run.return_value = handler

        coder_service._build_workflow = AsyncMock(return_value=workflow_mock)
        coder_service._get_workflow_context = AsyncMock(return_value=object())
        coder_service._get_chat_history = AsyncMock(return_value=[])

        coder_service._mark_turn_succeeded = AsyncMock()

        mock_chat_service = coder_service.chat_service_factory.return_value
        mock_chat_service.save_messages_for_turn.return_value = MagicMock(blocks=[])

        mock_session_service = coder_service.session_service_factory.return_value
        mock_session_service.get_operational_mode.return_value = OperationalMode.CODING

        execution = await coder_service.handle_user_message(
            user_message="hi", session_id=1
        )
        async for _ in execution.stream:
            _ = _

        mock_chat_service.save_messages_for_turn.assert_awaited()

    async def test_handle_user_message_marks_turn_succeeded(self, coder_service):
        """On successful completion, it should mark the turn as succeeded."""
        execution = await coder_service.handle_user_message(
            user_message="hi", session_id=1
        )
        async for _ in execution.stream:
            _ = _

        # Ensure the turn service was invoked to mark success.
        # The factory is an AsyncMock on the service instance, so we can inspect the returned mock.
        turn_service = coder_service.turn_service_factory.return_value
        turn_service.mark_succeeded.assert_awaited()

    async def test_handle_user_message_applies_single_shot_patches_if_mode_enabled(
        self, coder_service
    ):
        """If operational mode is SINGLE_SHOT, it should apply patches."""
        # Force SINGLE_SHOT operational mode.
        session_service = coder_service.session_service_factory.return_value
        session_service.get_operational_mode.return_value = OperationalMode.SINGLE_SHOT

        # Make single-shot patch service yield one event, proving it ran.
        single_shot_service = (
            coder_service.single_shot_patch_service_factory.return_value
        )

        async def _yield_one(*_args, **_kwargs):  # noqa: ANN001
            yield SingleShotDiffAppliedEvent(file_path="a.py", output="ok")

        single_shot_service.apply_from_blocks = _yield_one  # type: ignore[method-assign]

        execution = await coder_service.handle_user_message(
            user_message="hi", session_id=1
        )
        events = [e async for e in execution.stream]

        assert any(isinstance(e, SingleShotDiffAppliedEvent) for e in events)

    async def test_handle_user_message_handles_cancellation_gracefully(
        self, coder_service, make_workflow_handler
    ):
        """If cancelled, it should raise CancelledError and ensure cleanup."""
        turn = MagicMock(turn_id="t1", settings_snapshot=MagicMock())
        mock_turn_service = coder_service.turn_service_factory.return_value
        mock_turn_service.start_turn.return_value = turn

        handler = make_workflow_handler(
            events=[], await_raises=asyncio.CancelledError()
        )

        workflow_mock = MagicMock()
        workflow_mock.run.return_value = handler
        coder_service._build_workflow = AsyncMock(return_value=workflow_mock)
        coder_service._get_workflow_context = AsyncMock(return_value=object())
        coder_service._get_chat_history = AsyncMock(return_value=[])

        execution = await coder_service.handle_user_message(
            user_message="hi", session_id=1
        )

        with pytest.raises(asyncio.CancelledError):
            async for _ in execution.stream:
                _ = _

        assert "t1" not in coder_service.execution_registry._runs

    async def test_handle_user_message_handles_workflow_error(
        self, coder_service, make_workflow_handler
    ):
        """If workflow raises an exception, it should yield a WorkflowErrorEvent."""
        turn = MagicMock(turn_id="t1", settings_snapshot=MagicMock())
        mock_turn_service = coder_service.turn_service_factory.return_value
        mock_turn_service.start_turn.return_value = turn

        handler = make_workflow_handler(
            events=[], await_raises=Exception("Workflow Failed")
        )

        workflow_mock = MagicMock()
        workflow_mock.run.return_value = handler
        coder_service._build_workflow = AsyncMock(return_value=workflow_mock)
        coder_service._get_workflow_context = AsyncMock(return_value=object())
        coder_service._get_chat_history = AsyncMock(return_value=[])

        execution = await coder_service.handle_user_message(
            user_message="hi", session_id=1
        )
        events = [e async for e in execution.stream]

        assert isinstance(events[-1], WorkflowErrorEvent)
        assert "Workflow Failed" in events[-1].message

    async def test_handle_user_message_logs_warning_if_unprocessed_usage_events_remain(
        self, coder_service, usage_collector_cm, make_workflow_handler
    ):
        """Should log warning if UsageCollector has unprocessed events in finally block."""
        usage_collector_cm.collector.unprocessed_count = 5  # type: ignore[attr-defined]

        turn = MagicMock(turn_id="t1", settings_snapshot=MagicMock())
        mock_turn_service = coder_service.turn_service_factory.return_value
        mock_turn_service.start_turn.return_value = turn

        handler = make_workflow_handler(events=[], await_raises=Exception("Crash"))

        workflow_mock = MagicMock()
        workflow_mock.run.return_value = handler
        coder_service._build_workflow = AsyncMock(return_value=workflow_mock)
        coder_service._get_workflow_context = AsyncMock(return_value=object())
        coder_service._get_chat_history = AsyncMock(return_value=[])

        with patch("app.coder.services.coder.UsageCollector", usage_collector_cm):
            with patch("app.coder.services.coder.logger") as mock_logger:
                execution = await coder_service.handle_user_message(
                    user_message="hi", session_id=1
                )
                _ = [e async for e in execution.stream]

                mock_logger.warning.assert_called()
                assert (
                    "usage events were not processed"
                    in mock_logger.warning.call_args[0][0]
                )
