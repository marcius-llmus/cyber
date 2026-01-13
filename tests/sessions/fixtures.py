import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.sessions.models import ChatSession
from app.core.enums import OperationalMode
from app.projects.models import Project

@pytest.fixture
async def chat_session(db_session: AsyncSession, project: Project) -> ChatSession:
    session = ChatSession(name="Test Session", operational_mode=OperationalMode.CODING, project_id=project.id)
    db_session.add(session)
    await db_session.flush()
    await db_session.refresh(session)
    return session
