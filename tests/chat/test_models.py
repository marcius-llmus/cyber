import pytest
from llama_index.core.llms import MessageRole
from sqlalchemy.exc import IntegrityError

from app.chat.enums import ChatTurnStatus
from app.chat.models import ChatTurn, Message


class TestMessageModel:
    async def test_message_requires_session_id(self, db_session):
        """Message.session_id is non-nullable and should raise on flush when missing."""
        message = Message(turn_id="t1", role=MessageRole.USER)
        db_session.add(message)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_message_requires_turn_id(self, db_session, chat_session):
        """Message.turn_id is non-nullable and should raise on flush when missing."""
        message = Message(session_id=chat_session.id, role=MessageRole.USER)
        db_session.add(message)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_message_requires_role(self, db_session, chat_session):
        """Message.role is non-nullable and should raise on flush when missing."""
        message = Message(session_id=chat_session.id, turn_id="t1")
        db_session.add(message)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_message_blocks_default_empty_list(self, db_session, chat_session):
        """Message.blocks defaults to an empty list when not explicitly set."""
        message = Message(
            session_id=chat_session.id, turn_id="t1", role=MessageRole.USER
        )
        db_session.add(message)
        await db_session.flush()
        await db_session.refresh(message)
        assert message.blocks == []

    async def test_message_content_property_concatenates_text_blocks(self):
        """Message.content concatenates content of blocks where type == 'text'."""
        message = Message(
            blocks=[
                {"type": "text", "content": "Hello "},
                {"type": "tool", "content": "ignore me"},
                {"type": "text", "content": "World"},
            ]
        )
        assert message.content == "Hello World"

    async def test_message_tool_calls_property_extracts_tool_blocks(self):
        """Message.tool_calls returns tool blocks (blocks where type == 'tool')."""
        message = Message(
            blocks=[
                {"type": "text", "content": "text"},
                {"type": "tool", "tool_call_data": {"name": "test"}},
            ]
        )
        assert message.tool_calls == [
            {"type": "tool", "tool_call_data": {"name": "test"}},
        ]

    async def test_message_timestamp_defaults_to_now(self, db_session, chat_session):
        """Message.timestamp defaults to server time on insert."""
        message = Message(
            session_id=chat_session.id, turn_id="t1", role=MessageRole.USER
        )
        db_session.add(message)
        await db_session.flush()
        await db_session.refresh(message)
        assert message.timestamp is not None


class TestChatTurnModel:
    async def test_chat_turn_requires_session_id(self, db_session):
        """ChatTurn.session_id is non-nullable and should raise on flush when missing."""
        turn = ChatTurn(id="t1")
        db_session.add(turn)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_chat_turn_status_defaults_to_pending(self, db_session, chat_session):
        """ChatTurn.status defaults to PENDING when not explicitly set."""
        turn = ChatTurn(id="t1", session_id=chat_session.id)
        db_session.add(turn)
        await db_session.flush()
        await db_session.refresh(turn)
        assert turn.status == ChatTurnStatus.PENDING

    async def test_chat_turn_created_at_defaults_to_now(self, db_session, chat_session):
        """ChatTurn.created_at defaults to server time on insert."""
        turn = ChatTurn(id="t1", session_id=chat_session.id)
        db_session.add(turn)
        await db_session.flush()
        await db_session.refresh(turn)
        assert turn.created_at is not None

    async def test_chat_turn_updated_at_defaults_to_now_and_updates_on_change(
        self, db_session, chat_session
    ):
        """ChatTurn.updated_at defaults to server time and updates when the row is modified."""
        turn = ChatTurn(id="t1", session_id=chat_session.id)
        db_session.add(turn)
        await db_session.flush()
        await db_session.refresh(turn)

        initial_updated_at = turn.updated_at
        assert initial_updated_at is not None

        turn.status = ChatTurnStatus.SUCCEEDED
        await db_session.flush()
        await db_session.refresh(turn)

        assert turn.updated_at >= initial_updated_at
