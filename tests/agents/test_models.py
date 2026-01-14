"""Model tests for the agents app."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import WorkflowState
from app.core.enums import OperationalMode
from app.projects.models import Project
from app.sessions.models import ChatSession


class TestWorkflowStateModel:
    @pytest.mark.asyncio
    async def test_workflow_state_primary_key_is_session_id(
        self, db_session: AsyncSession, chat_session: ChatSession
    ):
        """WorkflowState should use session_id as its primary key."""
        session_id = chat_session.id
        workflow_state = WorkflowState(session_id=session_id, state={"step": "init"})
        db_session.add(workflow_state)
        await db_session.flush()

        # Retrieve by PK
        retrieved = await db_session.get(WorkflowState, session_id)
        assert retrieved is not None
        assert retrieved.session_id == session_id

    @pytest.mark.asyncio
    async def test_workflow_state_has_state_json_column(
        self, db_session: AsyncSession, chat_session: ChatSession, project: Project
    ):
        """WorkflowState should have a JSON state column that is non-nullable."""
        project_id = chat_session.project_id
        session_id = chat_session.id
        state_data = {"step": 1, "context": {"foo": "bar"}}
        workflow_state = WorkflowState(session_id=session_id, state=state_data)
        db_session.add(workflow_state)
        await db_session.flush()

        retrieved = await db_session.get(WorkflowState, session_id)
        assert retrieved.state == state_data

        # Test non-nullable constraint
        new_session = ChatSession(name="Invalid Session", operational_mode=OperationalMode.CODING, project_id=project_id)
        db_session.add(new_session)
        await db_session.flush()

        workflow_state_invalid = WorkflowState(session_id=new_session.id)
        db_session.add(workflow_state_invalid)

        # Flush should trigger the IntegrityError due to nullable=False
        with pytest.raises(IntegrityError):
            await db_session.flush()

    @pytest.mark.asyncio
    async def test_workflow_state_relationship_to_chat_session_is_defined(
        self, db_session: AsyncSession, chat_session: ChatSession
    ):
        """WorkflowState should define a relationship to ChatSession via `session`."""
        session_id = chat_session.id
        workflow_state = WorkflowState(session_id=session_id, state={})
        db_session.add(workflow_state)
        await db_session.flush()

        # Check relationship via join
        stmt = (
            select(WorkflowState)
            .join(WorkflowState.session)
            .where(ChatSession.id == session_id)
        )
        result = await db_session.execute(stmt)
        assert result.scalar_one() is not None

    @pytest.mark.asyncio
    async def test_workflow_state_fk_cascade_on_delete(
        self, db_session: AsyncSession, chat_session: ChatSession
    ):
        """WorkflowState.session_id FK should cascade on delete."""
        session_id = chat_session.id
        workflow_state = WorkflowState(session_id=session_id, state={})
        db_session.add(workflow_state)
        await db_session.flush()

        assert await db_session.get(WorkflowState, session_id) is not None

        await db_session.delete(chat_session)
        await db_session.flush()

        # We rely on a DB-level FK (ON DELETE CASCADE) for WorkflowState.session_id.
        # The database deletes the WorkflowState row when ChatSession is deleted.
        #
        # Important nuance (especially with a unit-of-work / request-scoped session):
        # SQLAlchemy's Session keeps an identity map (in-memory cache) and relationship
        # state for objects it has already seen. A DB cascade does *not* automatically
        # update/evict those in-memory objects, so within the same Session you can end
        # up observing stale state unless you explicitly expire/refresh.
        #
        # We intentionally expire the Session here so the next ORM lookup reflects the
        # database truth rather than returning cached state.
        #
        # Why not refresh(chat_session)?
        # - chat_session has been deleted, so it is not refreshable (refresh() will raise
        #   "Instance ... is not persistent within this Session").
        # - refresh() also doesn't help for verifying cascaded child deletion; we want a
        #   fresh lookup of WorkflowState after the cascade has occurred.
        # On commit, we expire everything
        db_session.expire_all()

        # Optional sanity check: the parent row should be gone as well.
        assert await db_session.get(ChatSession, session_id) is None

        assert await db_session.get(WorkflowState, session_id) is None
