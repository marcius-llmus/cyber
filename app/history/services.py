from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.services import ProjectService
from app.history.exceptions import ChatSessionNotFoundException
from app.history.models import ChatSession, Message
from app.history.repositories import ChatSessionRepository
from app.history.schemas import ChatSessionCreate


class HistoryService:
    def __init__(self, session_repo: ChatSessionRepository, project_service: ProjectService):
        self.session_repo = session_repo
        self.project_service = project_service

    def get_sessions_by_project(self, project_id: int) -> list[ChatSession]:
        return self.session_repo.list_by_project(project_id=project_id)

    def get_most_recent_session_by_project(self, project_id: int) -> ChatSession | None:
        return self.session_repo.get_most_recent_by_project(project_id=project_id)

    def create_session(self, session_in: ChatSessionCreate) -> ChatSession:
        return self.session_repo.create(obj_in=session_in)

    def set_active_session(self, session_id: int) -> ChatSession:
        session = self.get_session(session_id=session_id)

        # Deactivate all other sessions for this project
        self.session_repo.deactivate_all_for_project(project_id=session.project_id)

        # Activate the target session
        session.is_active = True
        self.session_repo.db.add(session)
        return session

    def delete_session(self, session_id_to_delete: int) -> bool:
        """Deletes a chat session.

        Returns:
            bool: True if the deleted session was the active one, False otherwise.
        """
        active_project = self.project_service.project_repo.get_active()
        if not active_project:
            raise ActiveProjectRequiredException("Cannot delete session without an active project.")

        session_to_delete = self.session_repo.get(pk=session_id_to_delete)
        if not session_to_delete:
            raise ChatSessionNotFoundException(f"Session with id {session_id_to_delete} not found.")

        was_active = session_to_delete.is_active
        self.session_repo.delete(pk=session_id_to_delete)

        return was_active

    def get_session(self, session_id: int) -> ChatSession:
        session = self.session_repo.get_with_messages(session_id=session_id)
        if not session:
            raise ChatSessionNotFoundException(f"Session with id {session_id} not found.")
        return session

    def get_messages_by_session(self, *, session_id: int) -> list[Message]:
        session = self.get_session(session_id=session_id)
        return session.messages


class HistoryPageService:
    def __init__(self, history_service: HistoryService, project_service: ProjectService):
        self.history_service = history_service
        self.project_service = project_service

    def get_history_page_data(self) -> dict:
        active_project = self.project_service.project_repo.get_active()
        sessions = self.history_service.get_sessions_by_project(project_id=active_project.id) if active_project else []
        return {"sessions": sessions}
