from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.factories import build_project_service
from app.sessions.repositories import ChatSessionRepository
from app.sessions.services import SessionService


async def build_session_service(db: AsyncSession) -> SessionService:
    repo = ChatSessionRepository(db=db)
    project_service = await build_project_service(db)
    return SessionService(session_repo=repo, project_service=project_service)
