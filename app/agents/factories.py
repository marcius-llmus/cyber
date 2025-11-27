from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import sessionmanager
from app.context.dependencies import build_repo_map_service, build_codebase_service
from app.settings.dependencies import build_settings_service
from app.llms.dependencies import build_llm_service
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import BaseTool
from app.coder.tools import ExecutionTools, FileSystemTools
from app.context.tools import SearchTools, ContextTools


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
    tools.extend(context_tools.get_tools())

    fs_tools = FileSystemTools(
        db=sessionmanager, settings=settings, session_id=session_id, codebase_service=codebase_service
    )
    tools.extend(fs_tools.get_tools())

    search_tools = SearchTools(
        db=sessionmanager, settings=settings, session_id=session_id, codebase_service=codebase_service
    )
    tools.extend(search_tools.get_tools())

    exec_tools = ExecutionTools(db=sessionmanager, settings=settings, session_id=session_id)
    tools.extend(exec_tools.get_tools())

    repo_map = await repo_map_service.generate_repo_map(session_id)

    system_prompt = f"""You are an expert AI software engineer.

Instructions:
1. Always explain your plan before executing tools.
2. After using a tool, analyze the result and explain what you found.
3. If you find the answer, summarize it clearly.
4. When listing files, mention the relevant ones you found.

REPOSITORY CONTEXT:
{repo_map}
"""

    return FunctionAgent(tools=tools, llm=llm, system_prompt=system_prompt)
