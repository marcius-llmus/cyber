from contextvars import ContextVar
import logging
from typing import Any

from llama_index.core.instrumentation import get_dispatcher
from llama_index.core.instrumentation.event_handlers import BaseEventHandler
from llama_index.core.instrumentation.events import BaseEvent
from llama_index.core.instrumentation.events.llm import (
    LLMChatEndEvent,
    LLMCompletionEndEvent,
    LLMPredictEndEvent,
    LLMStructuredPredictEndEvent,
)

logger = logging.getLogger(__name__)

# Private module-level ContextVar.
# Implementation detail: hidden from the rest of the app.
_usage_events_ctx: ContextVar[list[BaseEvent] | None] = ContextVar(
    "usage_events_ctx", default=None
)


class _GlobalTokenUsageEventHandler(BaseEventHandler):
    """
    Internal handler that listens to the global dispatcher but only records
    events if a local context is active (i.e., inside a UsageCollector block).
    """

    @classmethod
    def class_name(cls) -> str:
        return "GlobalTokenUsageEventHandler"

    def handle(self, event: BaseEvent, **kwargs: Any) -> None:
        if isinstance(
            event,
            (
                LLMChatEndEvent,
                LLMCompletionEndEvent,
                LLMPredictEndEvent,
                LLMStructuredPredictEndEvent,
            ),
        ):
            # Only append if a collector is active for this specific async task
            if (collector := _usage_events_ctx.get()) is not None:
                collector.append(event)


class UsageCollector:
    """
    Context manager to capture usage events for a specific workflow execution.
    """

    def __init__(self):
        self.events: list[BaseEvent] = []
        self._token = None
        self._processed_count = 0

    async def __aenter__(self) -> "UsageCollector":
        # Start capturing for this async context
        self._token = _usage_events_ctx.set(self.events)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Stop capturing and cleanup.
        # During forced shutdown (GeneratorExit), the context is dying and
        # resetting the token is pointless (and will raise ValueError).
        if exc_type is GeneratorExit:
            logger.info("Skipping UsageCollector context reset due to GeneratorExit (shutdown/close).")
            return

        if self._token is not None:
            _usage_events_ctx.reset(self._token)

    def consume(self) -> list[BaseEvent]:
        """
        Returns only the events added since the last consume call.
        Moves the internal cursor forward.
        """
        total_events = len(self.events)
        if self._processed_count >= total_events:
            return []

        batch = self.events[self._processed_count :]
        self._processed_count = total_events
        return batch

    @property
    def unprocessed_count(self) -> int:
        return len(self.events) - self._processed_count


# Register the global handler once at module import time.
dispatcher = get_dispatcher()
dispatcher.add_event_handler(_GlobalTokenUsageEventHandler())
