import uuid
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.dependencies import get_project_service
from app.projects.models import Project
from app.projects.repositories import ProjectRepository
from app.projects.services import ProjectPageService, ProjectService


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
def project_mock() -> Project:
    uid = uuid.uuid4()
    unique_path = f"/tmp/test_project_{uid}"
    return Project(name=f"Test Project {uid}", path=unique_path, is_active=True)


@pytest.fixture
def project_inactive_mock() -> Project:
    uid = uuid.uuid4()
    unique_path = f"/tmp/test_project_inactive_{uid}"
    return Project(name=f"Inactive Project {uid}", path=unique_path, is_active=False)


@pytest.fixture
def project_repository(db_session: AsyncSession) -> ProjectRepository:
    return ProjectRepository(db=db_session)


@pytest.fixture
def project_repository_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ProjectRepository, instance=True)


@pytest.fixture
def project_service(project_repository_mock: MagicMock) -> ProjectService:
    """Provides a ProjectService instance with a MOCKED repository for unit testing."""
    return ProjectService(project_repo=project_repository_mock)


@pytest.fixture
def project_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ProjectService, instance=True)


@pytest.fixture
def project_page_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ProjectPageService, instance=True)


@pytest.fixture
def override_get_project_service(client, project_service_mock: MagicMock):
    client.app.dependency_overrides[get_project_service] = lambda: project_service_mock
    yield
    client.app.dependency_overrides.clear()
