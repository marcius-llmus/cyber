"""Model tests for the chat app.

Skeleton-only: implement assertions later.

NOTE: Model tests are allowed to use db_session.
"""


class TestMessageModel:
    async def test_message_requires_session_id(self):
        """Message.session_id is non-nullable and should raise on flush when missing."""
        pass

    async def test_message_requires_turn_id(self):
        """Message.turn_id is non-nullable and should raise on flush when missing."""
        pass

    async def test_message_requires_role(self):
        """Message.role is non-nullable and should raise on flush when missing."""
        pass

    async def test_message_blocks_default_empty_list(self):
        """Message.blocks defaults to an empty list when not explicitly set."""
        pass

    async def test_message_content_property_concatenates_text_blocks(self):
        """Message.content concatenates content of blocks where type == 'text'."""
        pass

    async def test_message_tool_calls_property_extracts_tool_blocks(self):
        """Message.tool_calls returns tool_call_data for blocks where type == 'tool'."""
        pass

    async def test_message_timestamp_defaults_to_now(self):
        """Message.timestamp defaults to server time on insert."""
        pass


class TestChatTurnModel:
    async def test_chat_turn_requires_session_id(self):
        """ChatTurn.session_id is non-nullable and should raise on flush when missing."""
        pass

    async def test_chat_turn_status_defaults_to_pending(self):
        """ChatTurn.status defaults to PENDING when not explicitly set."""
        pass

    async def test_chat_turn_created_at_defaults_to_now(self):
        """ChatTurn.created_at defaults to server time on insert."""
        pass

    async def test_chat_turn_updated_at_defaults_to_now_and_updates_on_change(self):
        """ChatTurn.updated_at defaults to server time and updates when the row is modified."""
        pass