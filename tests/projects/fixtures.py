import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.models import Project
from app.projects.repositories import ProjectRepository
from app.projects.services import ProjectService


@pytest.fixture
async def project(db_session: AsyncSession) -> Project:
    uid = uuid.uuid4()
    unique_path = f"/tmp/test_project_{uid}"
    proj = Project(name=f"Test Project {uid}", path=unique_path, is_active=True)
    db_session.add(proj)
    await db_session.flush()
    await db_session.refresh(proj)
    return proj

@pytest.fixture
async def project_inactive(db_session: AsyncSession) -> Project:
    uid = uuid.uuid4()
    unique_path = f"/tmp/test_project_inactive_{uid}"
    proj = Project(name=f"Inactive Project {uid}", path=unique_path, is_active=False)
    db_session.add(proj)
    await db_session.flush()
    await db_session.refresh(proj)
    return proj


@pytest.fixture
def project_repository(db_session: AsyncSession) -> ProjectRepository:
    return ProjectRepository(db=db_session)


@pytest.fixture
def project_service(project_repository: ProjectRepository) -> ProjectService:
    return ProjectService(project_repo=project_repository)
