from sqlalchemy import select, delete

from app.commons.repositories import BaseRepository
from app.chat.models import Message


class MessageRepository(BaseRepository[Message]):
    model = Message

    async def list_by_session_id(self, session_id: int) -> list[Message]:
        stmt = select(self.model).where(self.model.session_id == session_id).order_by(self.model.id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_session_id(self, session_id: int) -> None:
        stmt = delete(self.model).where(self.model.session_id == session_id)
        await self.db.execute(stmt)
        await self.db.flush()
