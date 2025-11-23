from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repositories import MessageRepository
from app.chat.services import ChatService
from app.history.repositories import ChatSessionRepository
from app.history.services import HistoryService
from app.projects.repositories import ProjectRepository
from app.projects.services import ProjectService


async def chat_service_factory(db: AsyncSession) -> ChatService:
    """Manually constructs the ChatService stack."""
    project_repo = ProjectRepository(db)
    project_service = ProjectService(project_repo)
    session_repo = ChatSessionRepository(db)
    history_service = HistoryService(session_repo, project_service)
    message_repo = MessageRepository(db)
    return ChatService(message_repo, history_service, project_service)
