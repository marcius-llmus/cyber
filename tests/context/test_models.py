import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.context.models import ContextFile


async def test_context_file_creation(db_session: AsyncSession, chat_session, engine):
    """Test creating a ContextFile."""
    context_file = ContextFile(
        session_id=chat_session.id,
        file_path="src/utils.py",
    )
    db_session.add(context_file)
    await db_session.flush()
    await db_session.refresh(context_file)

    assert context_file.id is not None
    assert context_file.file_path == "src/utils.py"
    assert context_file.session_id == chat_session.id
    assert context_file.hit_count == 0  # Default value
    assert context_file.user_pinned is False  # Default value


async def test_context_file_unique_constraint(db_session: AsyncSession, chat_session):
    """Test that duplicate file paths for same session raise IntegrityError."""
    c1 = ContextFile(session_id=chat_session.id, file_path="dup.py")
    db_session.add(c1)
    await db_session.flush()

    c2 = ContextFile(session_id=chat_session.id, file_path="dup.py")
    db_session.add(c2)
    
    with pytest.raises(IntegrityError):
        await db_session.flush()