from unittest.mock import MagicMock
import uuid

import pytest
from llama_index.core.workflow import Workflow
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.repositories import WorkflowStateRepository
from app.agents.services import AgentContextService, WorkflowService
from app.context.services import CodebaseService, RepoMapService, WorkspaceService
from app.core.enums import OperationalMode
from app.projects.models import Project
from app.projects.services import ProjectService
from app.prompts.services import PromptService
from app.sessions.models import ChatSession


@pytest.fixture
async def project(db_session: AsyncSession) -> Project:
    uid = uuid.uuid4()
    unique_path = f"/tmp/test_project_{uid}"
    proj = Project(name=f"Test Project {uid}", path=unique_path)
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)
    return proj


@pytest.fixture
async def chat_session(db_session: AsyncSession, project: Project) -> ChatSession:
    session = ChatSession(name="Test Session", operational_mode=OperationalMode.CODING, project_id=project.id)
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.fixture
def workflow_state_repository(db_session: AsyncSession) -> WorkflowStateRepository:
    return WorkflowStateRepository(db=db_session)


@pytest.fixture
def workflow_service(
    workflow_state_repository: WorkflowStateRepository,
) -> WorkflowService:
    return WorkflowService(workflow_repo=workflow_state_repository)


@pytest.fixture
def repo_map_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(RepoMapService, instance=True)


@pytest.fixture
def workspace_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(WorkspaceService, instance=True)


@pytest.fixture
def codebase_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(CodebaseService, instance=True)


@pytest.fixture
def project_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(ProjectService, instance=True)


@pytest.fixture
def prompt_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(PromptService, instance=True)


@pytest.fixture
def agent_context_service(
    repo_map_service_mock: MagicMock,
    workspace_service_mock: MagicMock,
    codebase_service_mock: MagicMock,
    project_service_mock: MagicMock,
    prompt_service_mock: MagicMock,
) -> AgentContextService:
    return AgentContextService(
        repo_map_service=repo_map_service_mock,
        workspace_service=workspace_service_mock,
        codebase_service=codebase_service_mock,
        project_service=project_service_mock,
        prompt_service=prompt_service_mock,
    )


@pytest.fixture
def workflow_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(Workflow, instance=True)
