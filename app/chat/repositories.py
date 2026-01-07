from sqlalchemy import select, delete

from app.commons.repositories import BaseRepository
from app.chat.models import Message, ChatTurn


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


class ChatTurnRepository(BaseRepository[ChatTurn]):
    model = ChatTurn

    async def get_by_id_and_session(self, *, turn_id: str, session_id: int) -> ChatTurn | None:
        stmt = select(self.model).where(self.model.id == turn_id, self.model.session_id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
