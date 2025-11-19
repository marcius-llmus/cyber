from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.dependencies import get_chat_service, get_message_repository
from app.chat.services import ChatService
from app.coder.services import CoderPageService
from app.coder.services import CoderService
from app.history.dependencies import get_session_repository, get_history_service
from app.llms.dependencies import get_llm_factory
from app.projects.dependencies import get_project_repository, get_project_service
from app.settings.dependencies import (
    get_llm_settings_repository,
    get_settings_repository,
    get_llm_settings_service,
    get_settings_service
)
from app.usage.dependencies import get_usage_page_service, get_usage_service
from app.usage.services import UsagePageService
from app.agents.dependencies import get_workflow_factory


async def get_coder_page_service(
    usage_page_service: UsagePageService = Depends(get_usage_page_service),
    chat_service: ChatService = Depends(get_chat_service),
) -> CoderPageService:
    return CoderPageService(
        usage_page_service=usage_page_service, chat_service=chat_service
    )


async def get_coder_service_for_ws(db: AsyncSession) -> CoderService:
    """
    A dedicated dependency provider for the WebSocket context. It manually
    constructs the required services for a single conversational turn using a
    provided database session.
    """
    # Factories and simple services
    llm_factory = await get_llm_factory()
    usage_service = await get_usage_service()

    # Repositories
    message_repo = await get_message_repository(db=db)
    session_repo = await get_session_repository(db=db)
    project_repo = await get_project_repository(db=db)
    llm_settings_repo = await get_llm_settings_repository(db=db)
    settings_repo = await get_settings_repository(db=db)

    # Core Services
    project_service = await get_project_service(repo=project_repo)
    history_service = await get_history_service(repo=session_repo, project_service=project_service)
    chat_service = await get_chat_service(
        message_repo=message_repo, history_service=history_service, project_service=project_service
    )
    llm_settings_service = await get_llm_settings_service(llm_settings_repo=llm_settings_repo)
    settings_service = await get_settings_service(
        settings_repo=settings_repo, llm_settings_service=llm_settings_service, llm_factory=llm_factory
    )
    workflow_factory = await get_workflow_factory(llm_factory=llm_factory, settings_service=settings_service)
    coder_service = CoderService(
        chat_service=chat_service, usage_service=usage_service, workflow_factory=workflow_factory
    )
    return coder_service
