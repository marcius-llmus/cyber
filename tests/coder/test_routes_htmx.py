import pytest
from fastapi import status

class TestCoderHtmxRoutes:
    async def test_cancel_turn_calls_registry_cancel(self):
        """POST /coder/turns/{turn_id}/cancel should call registry.cancel and return partials."""
        pass

    async def test_cancel_turn_renders_correct_partials(self):
        """The response should include message_form, remove_user_message, and remove_ai_message."""
        pass
