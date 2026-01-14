"""Repository tests for the agents app."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

import pytest

from app.core.enums import OperationalMode
from app.agents.models import WorkflowState
from app.projects.models import Project
from app.agents.repositories import WorkflowStateRepository
from app.sessions.models import ChatSession


class TestWorkflowStateRepository:
    async def test_get_by_session_id_returns_none_when_missing(
        self, workflow_state_repository: WorkflowStateRepository
    ):
        """Should return None when no workflow state exists for the session id."""
        result = await workflow_state_repository.get_by_session_id(999999)
        assert result is None

    async def test_get_by_session_id_returns_record_when_present(
        self, workflow_state_repository: WorkflowStateRepository, chat_session: ChatSession
    ):
        """Should return the WorkflowState record when one exists for the session id."""
        state = {"step": "init"}
        await workflow_state_repository.save_state(chat_session.id, state)

        result = await workflow_state_repository.get_by_session_id(chat_session.id)
        assert result is not None
        assert result.session_id == chat_session.id
        assert result.state == state

    async def test_get_by_session_id_returns_latest_state(
        self, workflow_state_repository: WorkflowStateRepository, chat_session: ChatSession
    ):
        """Should return the current persisted state payload for the session id."""
        await workflow_state_repository.save_state(chat_session.id, {"v": 1})
        await workflow_state_repository.save_state(chat_session.id, {"v": 2})

        result = await workflow_state_repository.get_by_session_id(chat_session.id)
        assert result.state == {"v": 2}

    async def test_get_by_session_id_uses_correct_where_clause(
        self, workflow_state_repository: WorkflowStateRepository, chat_session: ChatSession, db_session, project: Project
    ):
        """get_by_session_id should filter by WorkflowState.session_id."""
        session_id = chat_session.id
        project_id = chat_session.project_id
        # Create another session to ensure we don't fetch its state
        other_session = ChatSession(name="Other Session", operational_mode=OperationalMode.CODING, project_id=project_id)
        db_session.add(other_session)
        await db_session.flush()
        await db_session.refresh(other_session)

        await workflow_state_repository.save_state(session_id, {"target": True})
        await workflow_state_repository.save_state(other_session.id, {"target": False})

        result = await workflow_state_repository.get_by_session_id(session_id)
        assert result.state == {"target": True}

    async def test_save_state_inserts_new_record(
        self, workflow_state_repository: WorkflowStateRepository, chat_session: ChatSession
    ):
        """Should insert a new WorkflowState record for a previously unseen session id."""
        state = {"new": "data"}
        saved = await workflow_state_repository.save_state(chat_session.id, state)
        assert saved.session_id == chat_session.id
        assert saved.state == state

        # Verify persistence
        in_db = await workflow_state_repository.get_by_session_id(chat_session.id)
        assert in_db is not None

    async def test_save_state_upserts_existing_record(
        self, workflow_state_repository: WorkflowStateRepository, chat_session: ChatSession
    ):
        """Should update (upsert) the WorkflowState record when the session id already exists."""
        await workflow_state_repository.save_state(chat_session.id, {"step": 1})
        updated = await workflow_state_repository.save_state(chat_session.id, {"step": 2})
        assert updated.state == {"step": 2}

    async def test_save_state_returns_persisted_model(
        self, workflow_state_repository: WorkflowStateRepository, chat_session: ChatSession
    ):
        """save_state should return the persisted WorkflowState model instance."""
        result = await workflow_state_repository.save_state(chat_session.id, {})
        assert isinstance(result, WorkflowState)
        assert result.session_id == chat_session.id

    async def test_save_state_flushes_changes(
        self, workflow_state_repository: WorkflowStateRepository, chat_session: ChatSession, db_session
    ):
        """save_state should flush so subsequent reads in the same session see the updated state."""

        await workflow_state_repository.save_state(chat_session.id, {"k": 1})
        # Direct SQL query to verify flush happened
        result = await db_session.execute(select(WorkflowState).where(WorkflowState.session_id == chat_session.id))
        assert result.scalar_one().state == {"k": 1}

    async def test_save_state_stores_json_round_trip(self, workflow_state_repository: WorkflowStateRepository, chat_session: ChatSession):
        """save_state should persist JSON such that nested dictionaries round-trip accurately."""
        complex_state = {"a": 1, "b": {"c": [1, 2, 3], "d": "text"}}
        await workflow_state_repository.save_state(chat_session.id, complex_state)
        retrieved = await workflow_state_repository.get_by_session_id(chat_session.id)
        assert retrieved.state == complex_state

    async def test_save_state_overwrites_previous_state_entirely(self, workflow_state_repository: WorkflowStateRepository, chat_session: ChatSession):
        """save_state should overwrite the prior state (replace semantics, not merge)."""
        await workflow_state_repository.save_state(chat_session.id, {"a": 1})
        await workflow_state_repository.save_state(chat_session.id, {"b": 2})
        retrieved = await workflow_state_repository.get_by_session_id(chat_session.id)
        assert retrieved.state == {"b": 2}

    async def test_save_state_rejects_non_dict_state(self, workflow_state_repository: WorkflowStateRepository, chat_session: ChatSession):
        """save_state should reject non-dict inputs to enforce repository contract."""
        with pytest.raises(ValueError):
            await workflow_state_repository.save_state(chat_session.id, "not a dict")

    async def test_save_state_does_not_commit(
        self,
        workflow_state_repository: WorkflowStateRepository,
        chat_session: ChatSession,
        db_session,
    ):
        """save_state should not commit; transaction boundaries are owned by higher layers."""
        await workflow_state_repository.save_state(chat_session.id, {"data": 1})
        await db_session.rollback()
        
        # Should be gone
        result = await workflow_state_repository.get_by_session_id(chat_session.id)
        assert result is None

    async def test_save_state_propagates_db_errors(
        self, workflow_state_repository: WorkflowStateRepository
    ):
        """save_state should surface underlying DB/SQLAlchemy errors."""
        # Try to save with a non-existent session_id, which should violate FK constraint
        # (assuming FKs are enforced, which they are in app/core/db.py for SQLite)
        with pytest.raises(IntegrityError):
            await workflow_state_repository.save_state(999999, {"fail": True})