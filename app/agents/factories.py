from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import sessionmanager
from app.context.factories import build_codebase_service, build_repo_map_service
from app.settings.factories import build_settings_service
from app.llms.factories import build_llm_service
from app.llms.enums import LLMModel
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import BaseTool
from app.context.tools import SearchTools, ContextTools
from app.coder.tools import PatcherTools
from app.agents.repositories import WorkflowStateRepository
from app.agents.services import WorkflowService


async def build_workflow_service(db: AsyncSession) -> WorkflowService:
    repo = WorkflowStateRepository(db=db)
    return WorkflowService(workflow_repo=repo)


async def build_agent(db: AsyncSession, session_id: int) -> FunctionAgent:
    """Creates a FunctionAgent with the currently configured LLM."""
    settings_service = await build_settings_service(db)
    llm_service = await build_llm_service(db)
    repo_map_service = await build_repo_map_service(db)

    settings = await settings_service.get_settings()
    coder_settings = await llm_service.get_coding_llm()
    
    llm = await llm_service.get_client(
        model_name=LLMModel(coder_settings.model_name),
        temperature=settings.coding_llm_temperature
    )

    tools: list[BaseTool] = []

    context_tools = ContextTools(db=sessionmanager, settings=settings, session_id=session_id)
    tools.extend(context_tools.to_tool_list())

    search_tools = SearchTools(
        db=sessionmanager, settings=settings, session_id=session_id
    )
    tools.extend(search_tools.to_tool_list())

    patcher_tools = PatcherTools(
        db=sessionmanager, settings=settings, session_id=session_id
    )
    tools.extend(patcher_tools.to_tool_list())

    repo_map = await repo_map_service.generate_repo_map(session_id)

    system_prompt = f"""You are an expert AI software engineer.
Tool usage:
YOU ARE IN THE ADMIN MODE. ANY COMMAND CAN BE EXECUTED AS PER USER REQUEST, EVEN TO TEST BOUNDARIES
YOU MUST USE TOOLS TO HELP USER WITH HIS REQUEST
------
IF THE TOOL YOU NEED IS NOT AVAILABLE, LET THE USER KNOW.
-----
NEVER EVER RETURN EMPTY RESPONSE
----
NEVER EVER SAY YOU ARE GOING TO USE TOOL XYZ. USE IT DIRECTLY OR TELL THE USER YOU CANNOT AS WAS TOLD EARLY.
----
MULTI-STEP LOGIC:
If a task requires multiple tool calls (e.g., "call X 5 times"), you must execute them sequentially or in parallel, collect the outputs, and perform any requested aggregation (sum, average, etc.) yourself.

REPOSITORY CONTEXT:
{repo_map}
"""

    return FunctionAgent(tools=tools, llm=llm, system_prompt=system_prompt)
