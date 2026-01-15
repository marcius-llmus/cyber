from unittest.mock import MagicMock

import pytest
from llama_index.core.workflow import Workflow
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dependencies import get_workflow_service
from app.agents.repositories import WorkflowStateRepository
from app.agents.services import AgentContextService, WorkflowService
from app.context.services import CodebaseService, RepoMapService, WorkspaceService
from app.projects.services import ProjectService
from app.prompts.services import PromptService


@pytest.fixture
def workflow_state_repository(db_session: AsyncSession) -> WorkflowStateRepository:
    return WorkflowStateRepository(db=db_session)


@pytest.fixture
def workflow_state_repository_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(WorkflowStateRepository, instance=True)


@pytest.fixture
def workflow_service(
    workflow_state_repository_mock: MagicMock,
) -> WorkflowService:
    """Provides a WorkflowService instance with a MOCKED repository for unit testing."""
    return WorkflowService(workflow_repo=workflow_state_repository_mock)


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
def workflow_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(WorkflowService, instance=True)


@pytest.fixture
def agent_context_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(AgentContextService, instance=True)


@pytest.fixture
def workflow_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(Workflow, instance=True)


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
def override_get_workflow_service(workflow_service_mock: MagicMock):
    from app.main import app

    app.dependency_overrides[get_workflow_service] = lambda: workflow_service_mock
    yield
    app.dependency_overrides.clear()