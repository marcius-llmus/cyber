from sqlalchemy import select

from app.commons.repositories import BaseRepository
from app.patches.enums import DiffPatchStatus
from app.patches.models import DiffPatch


class DiffPatchRepository(BaseRepository[DiffPatch]):
    model = DiffPatch

    async def list_pending_by_message(self, *, message_id: int) -> list[DiffPatch]:
        stmt = (
            select(self.model)
            .where(self.model.message_id == message_id)
            .where(self.model.status == DiffPatchStatus.PENDING)
            .order_by(self.model.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())