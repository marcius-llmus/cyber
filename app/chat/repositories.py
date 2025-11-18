from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.repositories import BaseRepository
from app.history.models import Message


class MessageRepository(BaseRepository[Message]):
    model = Message
    def __init__(self, db: AsyncSession):
        super().__init__(db)