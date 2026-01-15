import datetime
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.models import Project
from app.sessions.repositories import ChatSessionRepository
from app.sessions.models import ChatSession
from app.core.enums import OperationalMode


async def test_list_by_project_ordering(db_session: AsyncSession, chat_session_repository: ChatSessionRepository, project: Project):
    """Verify sessions are listed by created_at desc."""
    # Create earlier session
    session1 = ChatSession(name="Old", project_id=project.id, created_at=datetime.datetime(2023, 1, 1))
    db_session.add(session1)
    await db_session.flush()
    
    # Create newer session
    session2 = ChatSession(name="New", project_id=project.id, created_at=datetime.datetime(2023, 1, 2))
    db_session.add(session2)
    await db_session.flush()

    sessions = await chat_session_repository.list_by_project(project.id)
    assert len(sessions) == 2
    assert sessions[0].id == session2.id
    assert sessions[1].id == session1.id


async def test_get_most_recent_by_project(db_session: AsyncSession, chat_session_repository: ChatSessionRepository, project: Project):
    """Verify returns the latest session."""
    session1 = ChatSession(name="Old", project_id=project.id, created_at=datetime.datetime(2023, 1, 1))
    db_session.add(session1)
    await db_session.flush()
    
    session2 = ChatSession(name="New", project_id=project.id, created_at=datetime.datetime(2023, 1, 2))
    db_session.add(session2)
    await db_session.flush()

    recent = await chat_session_repository.get_most_recent_by_project(project.id)
    assert recent is not None
    assert recent.id == session2.id


async def test_deactivate_all_for_project(
    db_session: AsyncSession, chat_session_repository: ChatSessionRepository, project: Project
):
    """Verify batch deactivation."""
    session1 = ChatSession(name="S1", project_id=project.id, is_active=True)
    session2 = ChatSession(name="S2", project_id=project.id, is_active=True)
    db_session.add_all([session1, session2])
    await db_session.flush()

    await chat_session_repository.deactivate_all_for_project(project.id)
    await db_session.refresh(session1)
    await db_session.refresh(session2)

    assert not session1.is_active
    assert not session2.is_active


async def test_get_with_messages(db_session: AsyncSession, chat_session_repository: ChatSessionRepository, chat_session: ChatSession):
    """Verify specific fetch with eager loading."""
    fetched = await chat_session_repository.get_with_messages(chat_session.id)
    assert fetched is not None
    assert fetched.id == chat_session.id
    # Accessing messages should not raise error
    assert fetched.messages == []


async def test_activate(db_session: AsyncSession, chat_session_repository: ChatSessionRepository, chat_session: ChatSession):
    """Verify activation persistence and refresh."""
    assert not chat_session.is_active
    
    updated = await chat_session_repository.activate(chat_session)
    
    assert updated.is_active
    assert updated.id == chat_session.id
    
    # Verify persistence
    await db_session.refresh(chat_session)
    assert chat_session.is_active


@pytest.mark.parametrize("has_loaded_instance", [True, False])
async def test_chat_session_repository__deactivate_all_for_project__flushes_changes(
    has_loaded_instance: bool,
    db_session: AsyncSession,
    project: Project,
):
    """deactivate_all_for_project should flush so subsequent reads see the changes.

    Covers:
        - instances already loaded in the identity map
        - no pre-loaded instances

    Asserts:
        - after calling deactivate_all_for_project, a SELECT sees no active sessions
    """
    s1 = ChatSession(
        name="S1",
        project_id=project.id,
        is_active=True,
        operational_mode=OperationalMode.CODING,
    )
    s2 = ChatSession(
        name="S2",
        project_id=project.id,
        is_active=True,
        operational_mode=OperationalMode.CODING,
    )
    db_session.add_all([s1, s2])
    await db_session.flush()

    if has_loaded_instance:
        loaded = await db_session.get(ChatSession, s1.id)
        assert loaded is not None
        assert loaded.is_active is True

    repo = ChatSessionRepository(db_session)
    await repo.deactivate_all_for_project(project.id)

    result = await db_session.execute(
        select(ChatSession).where(
            ChatSession.project_id == project.id,
            ChatSession.is_active.is_(True),
        )
    )
    assert result.scalars().all() == []
