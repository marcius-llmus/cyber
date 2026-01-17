from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.repositories import WorkflowStateRepository
from app.agents.services import (
    AgentContextService,
    AgentFactoryService,
    WorkflowService,
)
from app.context.factories import (
    build_codebase_service,
    build_repo_map_service,
    build_workspace_service,
)
from app.llms.factories import build_llm_service
from app.projects.factories import build_project_service
from app.prompts.factories import build_prompt_service
from app.sessions.factories import build_session_service
from app.settings.factories import build_settings_service


async def build_workflow_service(db: AsyncSession) -> WorkflowService:
    repo = WorkflowStateRepository(db=db)
    return WorkflowService(workflow_repo=repo)


async def build_agent_context_service(db: AsyncSession) -> AgentContextService:
    repo_map_service = await build_repo_map_service(db)
    workspace_service = await build_workspace_service(db)
    codebase_service = await build_codebase_service()
    project_service = await build_project_service(db)
    prompt_service = await build_prompt_service(db)

    return AgentContextService(
        repo_map_service=repo_map_service,
        workspace_service=workspace_service,
        codebase_service=codebase_service,
        project_service=project_service,
        prompt_service=prompt_service,
    )


async def build_agent_factory_service(db: AsyncSession) -> AgentFactoryService:
    settings_service = await build_settings_service(db)
    llm_service = await build_llm_service(db)
    session_service = await build_session_service(db)
    agent_context_service = await build_agent_context_service(db)

    return AgentFactoryService(
        settings_service=settings_service,
        llm_service=llm_service,
        session_service=session_service,
        agent_context_service=agent_context_service,
    )


async def build_agent(db: AsyncSession, session_id: int, turn_id: str | None = None):
    agent_factory_service = await build_agent_factory_service(db)
    return await agent_factory_service.build_agent(
        session_id=session_id, turn_id=turn_id
    )
