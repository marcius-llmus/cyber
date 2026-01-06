import uuid
from typing import Any

from llama_index.core.llms import ChatMessage, MessageRole

from app.chat.repositories import MessageRepository
from app.chat.schemas import MessageCreate
from app.sessions.models import ChatSession
from app.chat.models import Message
from app.sessions.schemas import ChatSessionCreate
from app.sessions.services import SessionService
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.services import ProjectService


class ChatService:
    def __init__(
        self,
        message_repo: MessageRepository,
        session_service: SessionService,
        project_service: ProjectService,
    ):
        self.message_repo = message_repo
        self.session_service = session_service
        self.project_service = project_service

    async def get_or_create_active_session(self) -> ChatSession:
        active_project = await self.project_service.project_repo.get_active()
        if not active_project:
            raise ActiveProjectRequiredException("Cannot start a chat without an active project.")
        return await self.get_or_create_session_for_project(active_project.id)

    async def get_or_create_session_for_project(self, project_id: int) -> ChatSession:
        if session := await self.session_service.get_most_recent_session_by_project(project_id=project_id):
            return session

        session_in = ChatSessionCreate(name="New Session", project_id=project_id)
        return await self.session_service.create_session(session_in=session_in)

    async def add_user_message(self, *, content: str, session_id: int) -> Message:
        # Convert raw content to a text block
        blocks = [{
            "type": "text",
            "block_id": str(uuid.uuid4()),
            "content": content
        }]
        message_in = MessageCreate(
            session_id=session_id,
            role=MessageRole.USER,
            blocks=blocks,
        )
        return await self.message_repo.create(obj_in=message_in)

    async def add_ai_message(
        self,
        *,
        session_id: int,
        blocks: list[dict[str, Any]],
    ) -> Message:
        message_in = MessageCreate(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            blocks=blocks,
        )
        return await self.message_repo.create(obj_in=message_in)

    async def get_session_by_id(self, session_id: int) -> ChatSession:
        return await self.session_service.get_session(session_id=session_id)

    async def list_messages_by_session(self, *, session_id: int) -> list[Message]:
        return await self.message_repo.list_by_session_id(session_id=session_id)

    async def get_chat_history(self, session_id: int) -> list[ChatMessage]:
        db_messages = await self.list_messages_by_session(session_id=session_id)
        return [
            ChatMessage(role=msg.role, content=msg.content) for msg in db_messages
        ]

    async def save_turn(
        self,
        *,
        session_id: int,
        user_content: str,
        blocks: list[dict[str, Any]],
    ) -> Message:
        """
        Atomically saves the user message and the AI message constructed from the result DTO.
        """
        await self.add_user_message(session_id=session_id, content=user_content)
        return await self.add_ai_message(
            session_id=session_id,
            blocks=blocks,
        )

    async def clear_session_messages(self, session_id: int) -> None:
        """Deletes all messages for a given session."""
        await self.message_repo.delete_by_session_id(session_id=session_id)
