from sqlalchemy.ext.asyncio import AsyncSession
from app.history.repositories import ChatSessionRepository
from app.history.services import HistoryService
from app.projects.factories import build_project_service


async def build_history_service(db: AsyncSession) -> HistoryService:
    repo = ChatSessionRepository(db=db)
    project_service = await build_project_service(db)
    return HistoryService(session_repo=repo, project_service=project_service)
