from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.dependencies import get_db
from app.projects.dependencies import get_project_service, build_project_service
from app.projects.services import ProjectService
from app.history.repositories import ChatSessionRepository
from app.history.services import HistoryPageService, HistoryService


async def get_session_repository(db: AsyncSession = Depends(get_db)) -> ChatSessionRepository:
    return ChatSessionRepository(db=db)


async def build_history_service(db: AsyncSession) -> HistoryService:
    repo = ChatSessionRepository(db=db)
    project_service = await build_project_service(db)
    return HistoryService(session_repo=repo, project_service=project_service)


async def get_history_service(
    db: AsyncSession = Depends(get_db),
) -> HistoryService:
    return await build_history_service(db)


async def get_history_page_service(
    history_service: HistoryService = Depends(get_history_service),
    project_service: ProjectService = Depends(get_project_service),
) -> HistoryPageService:
    return HistoryPageService(history_service=history_service, project_service=project_service)
