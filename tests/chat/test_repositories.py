"""Repository tests for the chat app.

Skeleton-only: implement assertions later.

NOTE: Repository tests are allowed to use db_session.
"""


class TestMessageRepository:
    async def test_list_by_session_id_returns_empty_list_when_no_messages(self):
        """list_by_session_id returns [] when there are no Message rows for the session."""
        pass

    async def test_list_by_session_id_orders_by_id_ascending(self):
        """list_by_session_id orders messages by Message.id (ascending)."""
        pass

    async def test_delete_by_session_id_deletes_all_messages_for_session(self):
        """delete_by_session_id removes all messages for the given session_id and flushes."""
        pass


class TestChatTurnRepository:
    async def test_get_by_id_and_session_returns_none_when_missing(self):
        """get_by_id_and_session returns None when no row matches turn_id+session_id."""
        pass

    async def test_get_by_id_and_session_returns_row_when_present(self):
        """get_by_id_and_session returns a ChatTurn when it exists for the session."""
        pass