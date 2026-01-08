from sqlalchemy import select

from app.commons.repositories import BaseRepository
from app.patches.enums import DiffPatchStatus
from app.patches.models import DiffPatch


class DiffPatchRepository(BaseRepository[DiffPatch]):
    model = DiffPatch

    async def list_pending_by_turn(self, *, session_id: int, turn_id: str) -> list[DiffPatch]:
        stmt = (
            select(self.model)
            .where(self.model.session_id == session_id)
            .where(self.model.turn_id == turn_id)
            .where(self.model.status == DiffPatchStatus.PENDING)
            .order_by(self.model.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_turn(self, *, session_id: int, turn_id: str) -> list[DiffPatch]:
        stmt = (
            select(self.model)
            .where(self.model.session_id == session_id)
            .where(self.model.turn_id == turn_id)
            .order_by(self.model.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())