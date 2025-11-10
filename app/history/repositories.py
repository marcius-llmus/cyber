from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.commons.repositories import BaseRepository
from app.history.models import ChatSession, Message


class ChatSessionRepository(BaseRepository[ChatSession]):
    model = ChatSession

    def __init__(self, db: Session):
        super().__init__(db)

    def list_by_project(self, project_id: int) -> list[ChatSession]:
        statement = (
            select(self.model)
            .where(self.model.project_id == project_id)
            .options(joinedload(self.model.messages))
            .order_by(self.model.created_at.desc())
        )
        result = self.db.execute(statement)
        return list(result.unique().scalars().all())

    def get_with_messages(self, session_id: int) -> ChatSession | None:
        statement = (
            select(self.model)
            .where(self.model.id == session_id)
            .options(joinedload(self.model.messages))
        )
        result = self.db.execute(statement)
        return result.unique().scalar_one_or_none()

    def get_most_recent_by_project(self, project_id: int) -> ChatSession | None:
        return (
            self.db.query(self.model)
            .filter_by(project_id=project_id)
            .order_by(self.model.created_at.desc())
            .first()
        )

    def deactivate_all_for_project(self, project_id: int):
        self.db.query(self.model).filter_by(
            project_id=project_id, is_active=True
        ).update({"is_active": False})
