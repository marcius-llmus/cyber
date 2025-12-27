from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.commons.repositories import BaseRepository
from app.sessions.models import ChatSession


class ChatSessionRepository(BaseRepository[ChatSession]):
    model = ChatSession

    async def list_by_project(self, project_id: int) -> list[ChatSession]:
        statement = (
            select(self.model)
            .where(self.model.project_id == project_id)
            .options(joinedload(self.model.messages))
            .order_by(self.model.created_at.desc())
        )
        result = await self.db.execute(statement)
        return list(result.unique().scalars().all())

    async def get_with_messages(self, session_id: int) -> ChatSession | None:
        statement = (
            select(self.model)
            .where(self.model.id == session_id)
            .options(joinedload(self.model.messages))
        )
        result = await self.db.execute(statement)
        return result.unique().scalar_one_or_none()

    async def get_most_recent_by_project(self, project_id: int) -> ChatSession | None:
        result = await self.db.execute(
            select(self.model)
            .filter_by(project_id=project_id)
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def deactivate_all_for_project(self, project_id: int):
        sessions = await self.db.execute(
            select(self.model).filter_by(project_id=project_id, is_active=True)
        )
        for session in sessions.scalars().all():
            session.is_active = False

    async def activate(self, session: ChatSession) -> ChatSession:
        session.is_active = True
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session
