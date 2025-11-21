from fastapi import Depends
from app.llms.dependencies import get_llm_factory
from app.llms.factory import LLMFactory
from app.settings.dependencies import get_settings_service
from app.settings.services import SettingsService
from app.agents.factory import WorkflowFactory


async def get_workflow_factory(
    llm_factory: LLMFactory = Depends(get_llm_factory),
    settings_service: SettingsService = Depends(get_settings_service),
) -> WorkflowFactory:
    return WorkflowFactory(llm_factory=llm_factory, settings_service=settings_service)
