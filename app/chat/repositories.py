from sqlalchemy import select, delete

from app.commons.repositories import BaseRepository
from app.chat.models import Message, DiffPatch
from app.chat.enums import PatchStatus


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


class DiffPatchRepository(BaseRepository[DiffPatch]):
    model = DiffPatch

    async def list_pending_by_message(self, *, message_id: int) -> list[DiffPatch]:
        stmt = (
            select(self.model)
            .where(self.model.message_id == message_id)
            .where(self.model.status == PatchStatus.PENDING)
            .order_by(self.model.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
