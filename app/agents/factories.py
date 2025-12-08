from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import sessionmanager
from app.context.factories import build_repo_map_service, build_workspace_service, build_codebase_service
from app.settings.factories import build_settings_service
from app.llms.factories import build_llm_service
from app.llms.enums import LLMModel
from app.projects.factories import build_project_service
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import BaseTool
from app.context.tools import SearchTools, FileTools
from app.coder.tools import PatcherTools
from app.agents.repositories import WorkflowStateRepository
from app.agents.services import WorkflowService, AgentContextService


async def build_workflow_service(db: AsyncSession) -> WorkflowService:
    repo = WorkflowStateRepository(db=db)
    return WorkflowService(workflow_repo=repo)


async def build_agent_context_service(db: AsyncSession) -> AgentContextService:
    repo_map_service = await build_repo_map_service(db)
    workspace_service = await build_workspace_service(db)
    codebase_service = await build_codebase_service()
    project_service = await build_project_service(db)
    
    return AgentContextService(
        repo_map_service=repo_map_service,
        workspace_service=workspace_service,
        codebase_service=codebase_service,
        project_service=project_service
    )


async def build_agent(db: AsyncSession, session_id: int) -> FunctionAgent:
    """Creates a FunctionAgent with the currently configured LLM."""
    settings_service = await build_settings_service(db)
    llm_service = await build_llm_service(db)
    agent_context_service = await build_agent_context_service(db)

    settings = await settings_service.get_settings()
    coder_settings = await llm_service.get_coding_llm()
    
    llm = await llm_service.get_client(
        model_name=LLMModel(coder_settings.model_name),
        temperature=settings.coding_llm_temperature
    )

    tools: list[BaseTool] = []

    file_tools = FileTools(db=sessionmanager, settings=settings, session_id=session_id)
    tools.extend(file_tools.to_tool_list())

    search_tools = SearchTools(db=sessionmanager, settings=settings, session_id=session_id)
    tools.extend(search_tools.to_tool_list())

    patcher_tools = PatcherTools(db=sessionmanager, settings=settings, session_id=session_id)
    tools.extend(patcher_tools.to_tool_list())

    system_prompt = await agent_context_service.build_system_prompt(session_id)

    return FunctionAgent(tools=tools, llm=llm, system_prompt=system_prompt)
