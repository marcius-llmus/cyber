from app.chat.services import ChatService
from app.context.services import WorkspaceService
from app.prompts.enums import PromptEventType
from app.sessions.enums import SessionEventType
from app.settings.services import SettingsService
from app.usage.services import UsagePageService


class CoderPageService:
    """
    This service is responsible for aggregating data for the main coder page.
    It orchestrates calls to other page services to build the complete context
    needed for rendering the initial HTML page.
    """

    def __init__(
        self,
        usage_page_service: UsagePageService,
        chat_service: ChatService,
        context_service: WorkspaceService,
        settings_service: SettingsService,
    ):
        self.usage_page_service = usage_page_service
        self.chat_service = chat_service
        self.context_service = context_service
        self.settings_service = settings_service

    async def get_main_page_data(self, session_id: int | None = None) -> dict:
        """Aggregates data from various services for the main page view."""
        if session_id and (session := await self.chat_service.get_session_by_id(session_id=session_id)):
            usage_data = await self.usage_page_service.get_session_metrics_page_data()
            context_files = await self.context_service.get_active_context(session.id)
            page_data = {
                **usage_data,
                "session": session,
                "messages": session.messages,
                "files": context_files,
                "active_project": session.project,
            }
        else:
            page_data = await self._get_empty_session_data()

        settings = await self.settings_service.get_settings()
        return {
            **page_data,
            "PromptEventType": PromptEventType,
            "SessionEventType": SessionEventType,
            "settings": settings,
        }

    async def _get_empty_session_data(self) -> dict:
        active_project = await self.chat_service.project_service.get_active_project()
        usage_data = await self.usage_page_service.get_empty_metrics_page_data()
        return {
            **usage_data,
            "session": None,
            "messages": [],
            "files": [],
            "active_project": active_project,
        }
