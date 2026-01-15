from app.sessions.factories import build_session_service
from app.sessions.services import SessionService
from app.sessions.repositories import ChatSessionRepository


async def test_build_session_service(db_session_mock):
    """Verify factory wiring."""
    service = await build_session_service(db=db_session_mock)

    assert isinstance(service, SessionService)
    assert isinstance(service.session_repo, ChatSessionRepository)
    assert service.session_repo.db is db_session_mock
    assert service.project_service is not None