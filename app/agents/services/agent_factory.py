from __future__ import annotations

from llama_index.core.tools import BaseTool

from app.agents.services.agents_context import (
    AgentContextService,  # here we call directly as it is a local
)
from app.coder.agent import CoderAgent
from app.context.tools import FileTools, SearchTools
from app.core.db import sessionmanager
from app.core.enums import OperationalMode
from app.llms.enums import LLMModel
from app.llms.services import LLMService
from app.patches.tools import PatcherTools
from app.sessions.services import SessionService
from app.settings.services import SettingsService


class AgentFactoryService:
    def __init__(
        self,
        settings_service: SettingsService,
        llm_service: LLMService,
        session_service: SessionService,
        agent_context_service: AgentContextService,
    ):
        self.settings_service = settings_service
        self.llm_service = llm_service
        self.session_service = session_service
        self.agent_context_service = agent_context_service

    async def build_agent(
        self,
        session_id: int,
        *,
        turn_id: str | None = None,
    ) -> CoderAgent:
        settings = await self.settings_service.get_settings()
        coder_settings = await self.llm_service.get_coding_llm()

        llm = await self.llm_service.get_client(
            model_name=LLMModel(coder_settings.model_name),
            temperature=settings.coding_llm_temperature,
        )

        operational_mode = await self.session_service.get_operational_mode(session_id)
        tools: list[BaseTool] = []

        # Read-only tools: CODING, ASK, PLANNER
        if operational_mode in [
            OperationalMode.CODING,
            OperationalMode.ASK,
            OperationalMode.PLANNER,
        ]:
            search_tools = SearchTools(
                db=sessionmanager, settings=settings, session_id=session_id
            )
            tools.extend(search_tools.to_tool_list())

            file_tools = FileTools(
                db=sessionmanager,
                settings=settings,
                session_id=session_id,
                turn_id=turn_id,
            )
            tools.extend(file_tools.to_tool_list())

        # Write tools (patcher): CODING only
        if operational_mode == OperationalMode.CODING:
            patcher_tools = PatcherTools(
                db=sessionmanager,
                settings=settings,
                session_id=session_id,
                turn_id=turn_id,
            )
            tools.extend(patcher_tools.to_tool_list())

        system_prompt = await self.agent_context_service.build_system_prompt(
            session_id,
            operational_mode=operational_mode,
        )

        return CoderAgent(tools=tools, llm=llm, system_prompt=system_prompt)
