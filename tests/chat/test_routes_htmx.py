"""HTMX route tests for the chat app.

Skeleton-only: implement assertions later.
"""


class TestChatHtmxRoutes:
    async def test_clear_chat_requires_active_project(self):
        """POST /chat/clear raises 400 if no active project is found (ActiveProjectRequiredException)."""
        pass

    async def test_clear_chat_clears_session_messages_and_returns_empty_list(self):
        """POST /chat/clear calls chat_service.clear_session_messages and returns empty message list partial."""
        pass