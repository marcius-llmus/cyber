from fastapi import Depends
from sqlalchemy.orm import Session

from app.chat.repositories import MessageRepository
from app.chat.services import ChatService
from app.commons.dependencies import get_db
from app.history.dependencies import get_history_service
from app.history.services import HistoryService
from app.projects.dependencies import get_project_service
from app.projects.services import ProjectService


def get_message_repository(db: Session = Depends(get_db)) -> MessageRepository:
    return MessageRepository(db=db)


def get_chat_service(
    message_repo: MessageRepository = Depends(get_message_repository),
    history_service: HistoryService = Depends(get_history_service),
    project_service: ProjectService = Depends(get_project_service),
) -> ChatService:
    return ChatService(
        message_repo=message_repo,
        history_service=history_service,
        project_service=project_service,
    )
