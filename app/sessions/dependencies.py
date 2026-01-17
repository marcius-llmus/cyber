from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.dependencies import get_db
from app.projects.dependencies import get_project_service
from app.projects.services import ProjectService
from app.sessions.factories import build_session_service
from app.sessions.repositories import ChatSessionRepository
from app.sessions.services import SessionPageService, SessionService


async def get_session_repository(
    db: AsyncSession = Depends(get_db),
) -> ChatSessionRepository:
    return ChatSessionRepository(db=db)


async def get_session_service(
    db: AsyncSession = Depends(get_db),
) -> SessionService:
    return await build_session_service(db)


async def get_session_page_service(
    session_service: SessionService = Depends(get_session_service),
    project_service: ProjectService = Depends(get_project_service),
) -> SessionPageService:
    return SessionPageService(
        session_service=session_service, project_service=project_service
    )
