"""Schema tests for the chat app.

Skeleton-only: implement assertions later.
"""


class TestChatSchemas:
    async def test_message_create_validates_role(self):
        """MessageCreate requires a valid MessageRole enum value."""
        pass

    async def test_turn_request_requires_user_content(self):
        """TurnRequest validation fails if user_content is missing."""
        pass

    async def test_chat_turn_create_defaults_status_to_pending(self):
        """ChatTurnCreate sets status to PENDING if not provided."""
        pass

    async def test_chat_turn_update_requires_status(self):
        """ChatTurnUpdate validation fails if status is missing."""
        pass