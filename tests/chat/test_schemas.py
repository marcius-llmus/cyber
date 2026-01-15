import pytest
from pydantic import ValidationError
from app.chat.schemas import MessageCreate, TurnRequest, ChatTurnCreate, ChatTurnUpdate
from app.chat.enums import ChatTurnStatus
from llama_index.core.llms import MessageRole


class TestChatSchemas:
    async def test_message_create_validates_role(self):
        """MessageCreate requires a valid MessageRole enum value."""
        with pytest.raises(ValidationError):
            MessageCreate(session_id=1, turn_id="t1", role="INVALID", blocks=[])
        
        # Valid case
        msg = MessageCreate(session_id=1, turn_id="t1", role=MessageRole.USER, blocks=[])
        assert msg.role == MessageRole.USER

    async def test_turn_request_requires_user_content(self):
        """TurnRequest validation fails if user_content is missing."""
        with pytest.raises(ValidationError):
            TurnRequest(blocks=[])

    async def test_chat_turn_create_defaults_status_to_pending(self):
        """ChatTurnCreate sets status to PENDING if not provided."""
        turn = ChatTurnCreate(id="t1", session_id=1)
        assert turn.status == ChatTurnStatus.PENDING

    async def test_chat_turn_update_requires_status(self):
        """ChatTurnUpdate validation fails if status is missing."""
        with pytest.raises(ValidationError):
            ChatTurnUpdate()
            
        # Valid
        update = ChatTurnUpdate(status=ChatTurnStatus.SUCCEEDED)
        assert update.status == ChatTurnStatus.SUCCEEDED