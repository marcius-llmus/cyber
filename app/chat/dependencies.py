from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repositories import MessageRepository
from app.chat.services import ChatService
from app.commons.dependencies import get_db
from app.history.dependencies import get_history_service
from app.history.services import HistoryService
from app.projects.dependencies import get_project_service
from app.projects.services import ProjectService


async def get_message_repository(db: AsyncSession = Depends(get_db)) -> MessageRepository:
    return MessageRepository(db=db)


async def get_chat_service(
    message_repo: MessageRepository = Depends(get_message_repository),
    history_service: HistoryService = Depends(get_history_service),
    project_service: ProjectService = Depends(get_project_service),
) -> ChatService:
    return ChatService(
        message_repo=message_repo,
        history_service=history_service,
        project_service=project_service,
    )