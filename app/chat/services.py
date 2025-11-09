from app.chat.enums import MessageRole
from app.chat.repositories import MessageRepository
from app.chat.schemas import MessageCreate
from app.history.models import ChatSession, Message
from app.history.schemas import ChatSessionCreate
from app.history.services import HistoryService
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.services import ProjectService


class ChatService:
    def __init__(
        self,
        message_repo: MessageRepository,
        history_service: HistoryService,
        project_service: ProjectService,
    ):
        self.message_repo = message_repo
        self.history_service = history_service
        self.project_service = project_service

    def get_or_create_active_session(self) -> ChatSession:
        active_project = self.project_service.project_repo.get_active()
        if not active_project:
            raise ActiveProjectRequiredException("Cannot start a chat without an active project.")

        if session := self.history_service.get_most_recent_session_by_project(project_id=active_project.id):
            return session

        session_in = ChatSessionCreate(name="New Session", project_id=active_project.id)
        return self.history_service.create_session(session_in=session_in)

    def add_user_message(self, *, content: str, session_id: int) -> Message:
        message_in = MessageCreate(
            session_id=session_id,
            role=MessageRole.USER,
            content=content,
        )
        return self.message_repo.create(obj_in=message_in)

    def add_ai_message(self, *, content: str, session_id: int) -> Message:
        message_in = MessageCreate(
            session_id=session_id,
            role=MessageRole.AI,
            content=content,
        )
        return self.message_repo.create(obj_in=message_in)

    def get_session_by_id(self, session_id: int) -> ChatSession:
        return self.history_service.get_session(session_id=session_id)

    def get_messages_for_session(self, *, session_id: int) -> list[Message]:
        return self.history_service.get_messages_by_session(session_id=session_id)
