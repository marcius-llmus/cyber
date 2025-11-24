from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import BaseTool

from app.chat.factories import chat_service_factory
from app.coder.services import CoderService
from app.commons.tools import BaseToolSet
from app.context.tools import ContextTools
from app.core.db import sessionmanager
from app.llms.enums import LLMModel
from app.llms.factory import LLMFactory
from app.settings.factories import settings_service_factory
from app.settings.services import SettingsService


AVAILABLE_TOOL_SETS: list[type[BaseToolSet]] = [ContextTools]


# maybe we will add agent app later, but for now, it can live here
# home sweet home. that's your home, mr. ReactAgent :)
async def agent_factory(
    llm_factory: LLMFactory, settings_service: SettingsService
) -> FunctionAgent:
    """Creates a FunctionAgent with the currently configured LLM."""
    settings = await settings_service.get_settings()
    llm_model = LLMModel(settings.coding_llm_settings.model_name)
    llm_metadata = await llm_factory.get_llm(llm_model)
    api_key = await settings_service.llm_settings_service.get_api_key_for_provider(
        llm_metadata.provider
    )
    llm = await llm_factory.get_client(
        model_name=llm_model,
        temperature=settings.coding_llm_temperature,
        api_key=api_key,
    )

    tools: list[BaseTool] = []

    for ToolClass in AVAILABLE_TOOL_SETS:
        # In the future, we will check settings.enable_{slug}_tools here
        tool_instance = ToolClass(db=sessionmanager, settings=settings)
        tools.extend(tool_instance.get_tools())

    return FunctionAgent(tools=tools, llm=llm)


async def coder_service_factory() -> CoderService:
    """Manually constructs the CoderService for WebSocket usage."""
    llm_factory = LLMFactory()

    return CoderService(
        db=sessionmanager,
        llm_factory=llm_factory,
        chat_service_factory=chat_service_factory,
        settings_service_factory=settings_service_factory,
        agent_factory=agent_factory,
    )
