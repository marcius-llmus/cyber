import asyncio
from unittest.mock import patch

import pytest

from app.usage.event_handlers import UsageCollector


class TestUsageCollector:
    async def test_aexit_skips_reset_on_generator_exit(self):
        """__aexit__ should not call reset() if the async generator is closed (GeneratorExit)."""

        async def _agen():  # noqa: ANN001
            async with UsageCollector() as collector:
                yield collector

        with patch("app.usage.event_handlers._usage_events_ctx") as mock_ctx:
            mock_ctx.set.return_value = "test_token"

            gen = _agen()
            _ = await anext(gen)
            await gen.aclose()

            mock_ctx.reset.assert_not_called()

    async def test_aexit_calls_reset_on_cancelled_error(self):
        """__aexit__ should call reset() if the block exits with asyncio.CancelledError."""
        with patch("app.usage.event_handlers._usage_events_ctx") as mock_ctx:
            mock_ctx.set.return_value = "test_token"

            async def _run():
                async with UsageCollector():
                    raise asyncio.CancelledError()

            with pytest.raises(asyncio.CancelledError):
                await _run()

            mock_ctx.reset.assert_called_once_with("test_token")

    async def test_aexit_calls_reset_on_normal_exit(self):
        """__aexit__ should call reset() when exiting normally (no exception)."""
        with patch("app.usage.event_handlers._usage_events_ctx") as mock_ctx:
            mock_ctx.set.return_value = "test_token"

            async with UsageCollector():
                pass

            mock_ctx.reset.assert_called_once_with("test_token")

    async def test_aexit_raises_value_error_if_reset_fails_on_normal_exit(self):
        """If reset() raises ValueError during normal exit, it should propagate."""
        with patch("app.usage.event_handlers._usage_events_ctx") as mock_ctx:
            mock_ctx.set.return_value = "test_token"
            mock_ctx.reset.side_effect = ValueError("Context error")

            with pytest.raises(ValueError, match="Context error"):
                async with UsageCollector():
                    pass
