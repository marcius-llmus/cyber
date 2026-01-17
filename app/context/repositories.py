from sqlalchemy import delete, select

from app.commons.repositories import BaseRepository
from app.context.models import ContextFile


class ContextRepository(BaseRepository[ContextFile]):
    model = ContextFile

    async def get_by_session_and_path(
        self, session_id: int, file_path: str
    ) -> ContextFile | None:
        query = select(self.model).where(
            self.model.session_id == session_id, self.model.file_path == file_path
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_by_session(self, session_id: int) -> list[ContextFile]:
        query = (
            select(self.model)
            .where(self.model.session_id == session_id)
            .order_by(self.model.updated_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def delete_by_session_and_path(self, session_id: int, file_path: str) -> None:
        query = delete(self.model).where(
            self.model.session_id == session_id, self.model.file_path == file_path
        )
        await self.db.execute(query)
        await self.db.flush()

    async def delete_all_by_session(self, session_id: int) -> None:
        query = delete(self.model).where(self.model.session_id == session_id)
        await self.db.execute(query)
        await self.db.flush()

    async def delete_by_session_and_id(
        self, session_id: int, context_file_id: int
    ) -> None:
        query = delete(self.model).where(
            self.model.session_id == session_id, self.model.id == context_file_id
        )
        await self.db.execute(query)
        await self.db.flush()
