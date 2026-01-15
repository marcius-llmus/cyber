import pytest
from sqlalchemy import select

from app.sessions.repositories import ChatSessionRepository
from app.sessions.models import ChatSession


@pytest.mark.parametrize(
    "has_loaded_instance",
    [
        (True,),
        (False,),
    ],
)
async def test_chat_session_repository__deactivate_all_for_project__flushes_changes(
    has_loaded_instance: bool,
    db_session,
    project,
):
    """Scenario matrix: sessions are deactivated via repository method.

    Why: repository write methods must flush so subsequent reads in the same transaction
    can observe changes without the caller doing a manual flush.

    Covers:
        - instances already loaded in the identity map
        - no pre-loaded instances

    Asserts:
        - after calling deactivate_all_for_project, a SELECT sees no active sessions
    """
    s1 = ChatSession(name="S1", project_id=project.id, is_active=True)
    s2 = ChatSession(name="S2", project_id=project.id, is_active=True)
    db_session.add_all([s1, s2])
    await db_session.flush()

    if has_loaded_instance:
        loaded = await db_session.get(ChatSession, s1.id)
        assert loaded is not None
        assert loaded.is_active is True

    repo = ChatSessionRepository(db_session)
    await repo.deactivate_all_for_project(project.id)

    result = await db_session.execute(
        select(ChatSession).where(ChatSession.project_id == project.id, ChatSession.is_active.is_(True))
    )
    assert result.scalars().all() == []
