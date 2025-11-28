from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import sessionmanager
from app.context.dependencies import build_repo_map_service, build_codebase_service
from app.settings.dependencies import build_settings_service
from app.llms.dependencies import build_llm_service
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import BaseTool
from app.context.tools import SearchTools, ContextTools
from app.coder.tools import PatcherTools


async def build_agent(db: AsyncSession, session_id: int) -> FunctionAgent:
    """Creates a FunctionAgent with the currently configured LLM."""
    settings_service = await build_settings_service(db)
    llm_service = await build_llm_service(db)
    codebase_service = await build_codebase_service()
    repo_map_service = await build_repo_map_service(db)

    settings = await settings_service.get_settings()
    llm = await llm_service.get_coding_llm()

    tools: list[BaseTool] = []

    context_tools = ContextTools(db=sessionmanager, settings=settings, session_id=session_id)
    tools.extend(context_tools.to_tool_list())

    search_tools = SearchTools(
        db=sessionmanager, settings=settings, session_id=session_id, codebase_service=codebase_service
    )
    tools.extend(search_tools.to_tool_list())

    patcher_tools = PatcherTools(
        db=sessionmanager, settings=settings, session_id=session_id
    )
    tools.extend(patcher_tools.to_tool_list())

    repo_map = await repo_map_service.generate_repo_map(session_id)

    system_prompt = f"""You are an expert AI software engineer.
Tool usage:
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
