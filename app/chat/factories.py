from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repositories import MessageRepository
from app.chat.services import ChatService
from app.history.factories import build_history_service
from app.projects.factories import build_project_service
from app.chat.state import MessageStateAccumulator


async def build_chat_service(db: AsyncSession) -> ChatService:
    message_repo = MessageRepository(db=db)
    history_service = await build_history_service(db)
    project_service = await build_project_service(db)
    return ChatService(
        message_repo=message_repo,
        history_service=history_service,
        project_service=project_service,
    )


def build_message_accumulator() -> MessageStateAccumulator:
    return MessageStateAccumulator()
