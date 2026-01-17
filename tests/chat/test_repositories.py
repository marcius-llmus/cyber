from llama_index.core.llms import MessageRole

from app.chat.enums import ChatTurnStatus
from app.chat.models import ChatTurn, Message


class TestMessageRepository:
    async def test_list_by_session_id_returns_empty_list_when_no_messages(
        self, message_repository, chat_session
    ):
        """list_by_session_id returns [] when there are no Message rows for the session."""
        messages = await message_repository.list_by_session_id(chat_session.id)
        assert messages == []

    async def test_list_by_session_id_orders_by_id_ascending(
        self, message_repository, chat_session, db_session
    ):
        """list_by_session_id orders messages by Message.id (ascending)."""
        msg1 = Message(
            session_id=chat_session.id,
            turn_id="t1",
            role=MessageRole.USER,
            blocks=[{"type": "text", "content": "1"}],
        )
        msg2 = Message(
            session_id=chat_session.id,
            turn_id="t1",
            role=MessageRole.ASSISTANT,
            blocks=[{"type": "text", "content": "2"}],
        )
        db_session.add_all([msg1, msg2])
        await db_session.flush()

        messages = await message_repository.list_by_session_id(chat_session.id)
        assert len(messages) == 2
        assert messages[0].id < messages[1].id

    async def test_delete_by_session_id_deletes_all_messages_for_session(
        self, message_repository, chat_session, db_session
    ):
        """delete_by_session_id removes all messages for the given session_id and flushes."""
        msg = Message(
            session_id=chat_session.id,
            turn_id="t1",
            role=MessageRole.USER,
            blocks=[{"type": "text", "content": "hi"}],
        )
        db_session.add(msg)
        await db_session.flush()

        await message_repository.delete_by_session_id(chat_session.id)

        messages = await message_repository.list_by_session_id(chat_session.id)
        assert messages == []


class TestChatTurnRepository:
    async def test_get_by_id_and_session_returns_none_when_missing(
        self, chat_turn_repository, chat_session
    ):
        """get_by_id_and_session returns None when no row matches turn_id+session_id."""
        turn = await chat_turn_repository.get_by_id_and_session(
            turn_id="missing", session_id=chat_session.id
        )
        assert turn is None

    async def test_get_by_id_and_session_returns_row_when_present(
        self, chat_turn_repository, chat_session, db_session
    ):
        """get_by_id_and_session returns a ChatTurn when it exists for the session."""
        turn = ChatTurn(
            id="t1", session_id=chat_session.id, status=ChatTurnStatus.PENDING
        )
        db_session.add(turn)
        await db_session.flush()

        result = await chat_turn_repository.get_by_id_and_session(
            turn_id="t1", session_id=chat_session.id
        )
        assert result is not None
        assert result.id == "t1"
        assert result.session_id == chat_session.id
