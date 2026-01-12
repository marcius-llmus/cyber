import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.projects.models import Project

@pytest.fixture
async def project(db_session: AsyncSession) -> Project:
    uid = uuid.uuid4()
    unique_path = f"/tmp/test_project_{uid}"
    proj = Project(name=f"Test Project {uid}", path=unique_path)
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)
    return proj