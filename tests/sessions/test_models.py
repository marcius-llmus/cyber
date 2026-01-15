"""Model tests for the sessions app."""
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import OperationalMode
from app.projects.models import Project
from app.sessions.models import ChatSession


async def test_chat_session_constraints(db_session: AsyncSession, project: Project):
    """Verify name and project_id are required."""
    # Test missing name
    session = ChatSession(project_id=project.id, operational_mode=OperationalMode.CODING)
    db_session.add(session)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # Test missing project_id
    session = ChatSession(name="No Project")
    db_session.add(session)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_chat_session_defaults(db_session: AsyncSession, project: Project):
    """Verify default values for new sessions."""
    session = ChatSession(name="Defaults", project_id=project.id)
    db_session.add(session)
    await db_session.flush()
    await db_session.refresh(session)

    assert session.is_active is False
    assert session.operational_mode == OperationalMode.CODING
    assert session.created_at is not None
    assert session.updated_at is not None


async def test_chat_session_relationships(db_session: AsyncSession, project: Project):
    """Verify relationships load correctly."""
    session = ChatSession(name="Rel Test", project_id=project.id)
    db_session.add(session)
    await db_session.flush()
    await db_session.refresh(session)

    # Test project relationship
    assert session.project.id == project.id


async def test_chat_session_cascade_from_project(db_session: AsyncSession, project: Project):
    """Verify session is deleted when project is deleted."""
    session = ChatSession(name="Cascade Test", project_id=project.id)
    session_id = session.id
    db_session.add(session)
    await db_session.flush()

    await db_session.delete(project)
    await db_session.flush()
    db_session.expire_all()

    result = await db_session.get(ChatSession, session_id)
    assert result is None
