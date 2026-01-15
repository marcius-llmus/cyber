from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.services import ProjectService
from app.core.enums import OperationalMode
from app.sessions.exceptions import ChatSessionNotFoundException
from app.sessions.models import ChatSession
from app.sessions.repositories import ChatSessionRepository
from app.sessions.schemas import ChatSessionCreate, ChatSessionUpdate


class SessionService:
    def __init__(self, session_repo: ChatSessionRepository, project_service: ProjectService):
        self.session_repo = session_repo
        self.project_service = project_service

    async def get_sessions_by_project(self, project_id: int) -> list[ChatSession]:
        return await self.session_repo.list_by_project(project_id=project_id)

    async def get_most_recent_session_by_project(self, project_id: int) -> ChatSession | None:
        return await self.session_repo.get_most_recent_by_project(project_id=project_id)

    async def create_session(self, session_in: ChatSessionCreate) -> ChatSession:
        return await self.session_repo.create(obj_in=session_in)

    async def set_active_session(self, session_id: int) -> ChatSession:
        session = await self.get_session(session_id=session_id)

        # Ensure the project associated with this session is active
        await self.project_service.set_active_project(session.project_id)

        # Deactivate all other sessions for this project
        await self.session_repo.deactivate_all_for_project(project_id=session.project_id)

        # Activate the target session
        session = await self.session_repo.activate(session)

        await self.project_service.set_active_project(project_id=session.project_id)

        return session

    async def delete_session(self, session_id_to_delete: int) -> bool:
        """Deletes a chat session.

        Returns:
            bool: True if the deleted session was the active one, False otherwise.
        """
        active_project = await self.project_service.project_repo.get_active()
        if not active_project:
            raise ActiveProjectRequiredException("Cannot delete session without an active project.")

        session_to_delete = await self.session_repo.get(pk=session_id_to_delete)
        if not session_to_delete:
            raise ChatSessionNotFoundException(f"Session with id {session_id_to_delete} not found.")

        was_active = session_to_delete.is_active
        await self.session_repo.delete(pk=session_id_to_delete)

        return was_active

    async def get_session(self, session_id: int) -> ChatSession:
        session = await self.session_repo.get_with_messages(session_id=session_id)
        if not session:
            raise ChatSessionNotFoundException(f"Session with id {session_id} not found.")
        return session

    async def get_operational_mode(self, session_id: int) -> OperationalMode:
        session = await self.get_session(session_id=session_id)
        return session.operational_mode

    async def set_operational_mode(self, session_id: int, mode: OperationalMode) -> ChatSession:
        return await self._update_session(session_id=session_id, obj_in=ChatSessionUpdate(operational_mode=mode))

    async def rename_session(self, session_id: int, name: str) -> ChatSession:
        if not (normalized := name.strip()):
            raise ValueError("Session name cannot be empty")
        return await self._update_session(session_id=session_id, obj_in=ChatSessionUpdate(name=normalized))

    async def _update_session(self, session_id: int, obj_in: ChatSessionUpdate) -> ChatSession:
        session = await self.get_session(session_id=session_id)
        return await self.session_repo.update(db_obj=session, obj_in=obj_in)


class SessionPageService:
    def __init__(self, session_service: SessionService, project_service: ProjectService):
        self.session_service = session_service
        self.project_service = project_service

    async def get_sessions_page_data(self) -> dict:
        active_project = await self.project_service.project_repo.get_active()
        sessions = await self.session_service.get_sessions_by_project(project_id=active_project.id) if active_project else []
        return {"sessions": sessions}
