import asyncio
import logging

from app.coder.schemas import TurnExecution

logger = logging.getLogger(__name__)


class TurnExecutionRegistry:
    """
    In-memory registry of currently running workflow handlers.
    Allows looking up and cancelling runs by turn_id.
    """

    def __init__(self) -> None:
        self._runs: dict[str, TurnExecution] = {}
        self._lock = asyncio.Lock()

    async def register(self, execution: TurnExecution) -> None:
        async with self._lock:
            self._runs[execution.turn.turn_id] = execution
            logger.debug(f"Registered active run for turn {execution.turn.turn_id}")

    async def cancel(self, *, turn_id: str) -> str | None:
        """
        Cancels the run and returns the original message (for UI restore).
        Returns None if run not found.
        """
        async with self._lock:
            run = self._runs.get(turn_id)

        if not run:
            logger.warning(f"Attempted to cancel unknown or finished run {turn_id}")
            return None

        await run.cancel()

        return run.user_message

    async def unregister(self, *, turn_id: str) -> None:
        async with self._lock:
            if turn_id in self._runs:
                del self._runs[turn_id]
                logger.debug(f"Unregistered run for turn {turn_id}")

_registry: TurnExecutionRegistry | None = None

def initialize_global_registry(registry: TurnExecutionRegistry) -> None:
    global _registry
    _registry = registry

def get_global_registry() -> TurnExecutionRegistry:
    if _registry is None:
        raise RuntimeError("TurnExecutionRegistry is not initialized. Call initialize_global_registry() first.")
    return _registry
