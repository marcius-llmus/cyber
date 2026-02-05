from unittest.mock import AsyncMock, MagicMock

from app.coder.services.execution_registry import TurnExecution, TurnExecutionRegistry


class TestTurnExecutionRegistry:
    async def test_register_adds_execution(self):
        """register should add the execution to the internal dict."""
        registry = TurnExecutionRegistry()
        turn = MagicMock()
        turn.turn_id = "t1"

        async def _stream():
            if False:  # pragma: no cover
                yield None

        execution = TurnExecution(turn=turn, stream=_stream(), user_message="hi")

        await registry.register(execution)
        assert registry._runs["t1"] == execution

    async def test_cancel_calls_execution_cancel(self):
        """cancel should lookup the execution and cancel its handler."""
        registry = TurnExecutionRegistry()
        turn = MagicMock()
        turn.turn_id = "t1"
        handler = AsyncMock()

        async def _stream():
            if False:  # pragma: no cover
                yield None

        execution = TurnExecution(
            turn=turn, stream=_stream(), user_message="hi", handler=handler
        )

        await registry.register(execution)

        result = await registry.cancel(turn_id="t1")

        assert result == execution
        handler.cancel_run.assert_awaited_once()

    async def test_unregister_removes_execution(self):
        """unregister should remove the execution from the internal dict."""
        registry = TurnExecutionRegistry()
        turn = MagicMock()
        turn.turn_id = "t1"

        async def _stream():
            if False:  # pragma: no cover
                yield None

        execution = TurnExecution(turn=turn, stream=_stream(), user_message="hi")
        await registry.register(execution)

        await registry.unregister(turn_id="t1")
        assert "t1" not in registry._runs


class TestTurnExecution:
    async def test_cancel_calls_handler_cancel_run(self):
        """cancel should call handler.cancel_run() if handler is present."""
        turn = MagicMock()
        turn.turn_id = "t1"
        handler = AsyncMock()

        async def _stream():
            if False:  # pragma: no cover
                yield None

        execution = TurnExecution(
            turn=turn, stream=_stream(), user_message="hi", handler=handler
        )

        await execution.cancel()
        handler.cancel_run.assert_awaited_once()
