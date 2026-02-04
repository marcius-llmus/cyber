import pytest
from app.coder.services.execution_registry import TurnExecutionRegistry, TurnExecution

class TestTurnExecutionRegistry:
    async def test_register_adds_execution(self):
        """register should add the execution to the internal dict."""
        pass

    async def test_cancel_calls_execution_cancel(self):
        """cancel should lookup the execution and call its cancel method."""
        pass

    async def test_unregister_removes_execution(self):
        """unregister should remove the execution from the internal dict."""
        pass

class TestTurnExecution:
    async def test_cancel_calls_handler_cancel_run(self):
        """cancel should call handler.cancel_run() if handler is present."""
        pass
