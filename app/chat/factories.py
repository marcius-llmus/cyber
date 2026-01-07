from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repositories import MessageRepository
from app.chat.services import ChatService
from app.sessions.factories import build_session_service
from app.projects.factories import build_project_service
from app.chat.repositories import ChatTurnRepository
from app.chat.services.turn import ChatTurnService


async def build_chat_service(db: AsyncSession) -> ChatService:
    message_repo = MessageRepository(db=db)
    session_service = await build_session_service(db)
    project_service = await build_project_service(db)
    return ChatService(
        message_repo=message_repo,
        session_service=session_service,
        project_service=project_service,
    )


async def build_chat_turn_service(db: AsyncSession) -> ChatTurnService:
    return ChatTurnService(turn_repo=ChatTurnRepository(db=db))
