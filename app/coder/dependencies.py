from fastapi import Depends

from app.agents.factories import build_agent, build_workflow_service
from app.chat.dependencies import get_chat_service
from app.chat.factories import build_chat_service, build_chat_turn_service
from app.chat.services import ChatService
from app.coder.factories import (
    build_messaging_turn_event_handler,
    build_single_shot_patch_service,
)
from app.coder.services import CoderPageService, CoderService
from app.context.dependencies import get_context_service
from app.context.factories import build_workspace_service
from app.context.services import WorkspaceService
from app.core.db import sessionmanager
from app.patches.factories import build_diff_patch_service
from app.sessions.factories import build_session_service
from app.settings.dependencies import get_settings_service
from app.settings.factories import build_settings_service
from app.settings.services import SettingsService
from app.usage.dependencies import get_usage_page_service
from app.usage.factories import build_usage_service
from app.usage.services import UsagePageService


async def get_coder_page_service(
    usage_page_service: UsagePageService = Depends(get_usage_page_service),
    chat_service: ChatService = Depends(get_chat_service),
    context_service: WorkspaceService = Depends(get_context_service),
    settings_service: SettingsService = Depends(get_settings_service),
) -> CoderPageService:
    return CoderPageService(
        usage_page_service=usage_page_service,
        chat_service=chat_service,
        context_service=context_service,
        settings_service=settings_service,
    )


async def get_coder_service() -> CoderService:
    return CoderService(
        db=sessionmanager,
        chat_service_factory=build_chat_service,
        turn_service_factory=build_chat_turn_service,
        session_service_factory=build_session_service,
        workflow_service_factory=build_workflow_service,
        settings_service_factory=build_settings_service,
        usage_service_factory=build_usage_service,
        agent_factory=build_agent,
        turn_handler_factory=build_messaging_turn_event_handler,
        diff_patch_service_factory=build_diff_patch_service,
        context_service_factory=build_workspace_service,
        single_shot_patch_service_factory=build_single_shot_patch_service,
    )
