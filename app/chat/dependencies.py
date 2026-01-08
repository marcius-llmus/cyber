from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repositories import MessageRepository
from app.chat.services import ChatService
from app.commons.dependencies import get_db
from app.chat.factories import build_chat_service, build_chat_turn_service
from app.chat.services.turn import ChatTurnService


async def get_message_repository(db: AsyncSession = Depends(get_db)) -> MessageRepository:
    return MessageRepository(db=db)


async def get_chat_service(
    db: AsyncSession = Depends(get_db),
) -> ChatService:
    return await build_chat_service(db)


async def get_chat_turn_service(db: AsyncSession = Depends(get_db)) -> ChatTurnService:
    return await build_chat_turn_service(db)
