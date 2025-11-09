from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.tools import BaseTool

from app.llms.enums import LLMModel
from app.llms.factory import LLMFactory
from app.settings.services import SettingsService


class WorkflowFactory:
    def __init__(self, llm_factory: LLMFactory, settings_service: SettingsService):
        self.llm_factory = llm_factory
        self.settings_service = settings_service

    async def create_function_agent(self, tools: list[BaseTool]) -> FunctionAgent:
        """Creates a FunctionAgent with the currently configured LLM."""
        settings = self.settings_service.get_settings()
        llm_model = LLMModel(settings.coding_llm_settings.model_name)
        llm_metadata = self.llm_factory.get_llm(llm_model)
        api_key = self.settings_service.llm_settings_service.get_api_key_for_provider(
            llm_metadata.provider
        )
        llm = self.llm_factory.get_client(
            model_name=llm_model,
            temperature=settings.coding_llm_temperature,
            api_key=api_key,
        )
        return FunctionAgent(tools=tools, llm=llm)
