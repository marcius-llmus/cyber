from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repositories import MessageRepository
from app.chat.services import ChatService
from app.commons.dependencies import get_db
from app.history.dependencies import build_history_service
from app.projects.dependencies import build_project_service


async def get_message_repository(db: AsyncSession = Depends(get_db)) -> MessageRepository:
    return MessageRepository(db=db)


async def build_chat_service(db: AsyncSession) -> ChatService:
    message_repo = MessageRepository(db=db)
    history_service = await build_history_service(db)
    project_service = await build_project_service(db)
    return ChatService(
        message_repo=message_repo,
        history_service=history_service,
        project_service=project_service,
    )


async def get_chat_service(
    db: AsyncSession = Depends(get_db),
) -> ChatService:
    return await build_chat_service(db)
