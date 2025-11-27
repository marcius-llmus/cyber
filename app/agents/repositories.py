from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert

from app.commons.repositories import BaseRepository
from app.agents.models import WorkflowState


class WorkflowStateRepository(BaseRepository[WorkflowState]):
    model = WorkflowState

    async def get_by_session_id(self, session_id: int) -> WorkflowState | None:
        stmt = select(self.model).where(self.model.session_id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def save_state(self, session_id: int, state: dict) -> WorkflowState:
        stmt = insert(self.model).values(
            session_id=session_id, state=state
        ).on_conflict_do_update(
            index_elements=[self.model.session_id],
            set_={"state": state}
        ).returning(self.model)
        
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.scalar_one()

    async def delete_by_session_id(self, session_id: int) -> None:
        """Explicitly deletes the workflow state for a given session."""
        query = delete(self.model).where(self.model.session_id == session_id)
        await self.db.execute(query)
        await self.db.flush()
