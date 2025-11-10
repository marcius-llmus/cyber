from fastapi import Depends
from sqlalchemy.orm import Session

from app.commons.dependencies import get_db
from app.projects.dependencies import get_project_service
from app.projects.services import ProjectService
from app.history.repositories import ChatSessionRepository
from app.history.services import HistoryPageService, HistoryService


def get_session_repository(db: Session = Depends(get_db)) -> ChatSessionRepository:
    return ChatSessionRepository(db=db)


def get_history_service(
    repo: ChatSessionRepository = Depends(get_session_repository),
    project_service: ProjectService = Depends(get_project_service),
) -> HistoryService:
    return HistoryService(session_repo=repo, project_service=project_service)


def get_history_page_service(
    history_service: HistoryService = Depends(get_history_service),
    project_service: ProjectService = Depends(get_project_service),
) -> HistoryPageService:
    return HistoryPageService(history_service=history_service, project_service=project_service)