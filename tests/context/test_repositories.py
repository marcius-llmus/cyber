from app.context.repositories import ContextRepository
from app.context.schemas import ContextFileCreate


async def test_create_context_file(context_repository: ContextRepository, chat_session):
    """Test creating a context file via repository."""
    obj_in = ContextFileCreate(session_id=chat_session.id, file_path="src/main.py")
    context_file = await context_repository.create(obj_in)

    assert context_file.id is not None
    assert context_file.file_path == "src/main.py"
    assert context_file.session_id == chat_session.id


async def test_get_by_session_and_path(
    context_repository: ContextRepository, context_file
):
    """Test retrieving a context file by session and path."""
    result = await context_repository.get_by_session_and_path(
        context_file.session_id, context_file.file_path
    )
    assert result is not None
    assert result.id == context_file.id
    assert result.file_path == context_file.file_path


async def test_list_by_session(context_repository: ContextRepository, context_file):
    """Test listing context files for a session."""
    results = await context_repository.list_by_session(context_file.session_id)
    assert len(results) == 1
    assert results[0].id == context_file.id


async def test_delete_by_session_and_path(
    context_repository: ContextRepository, context_file
):
    """Test deleting a context file by path."""
    await context_repository.delete_by_session_and_path(
        context_file.session_id, context_file.file_path
    )
    result = await context_repository.get_by_session_and_path(
        context_file.session_id, context_file.file_path
    )
    assert result is None


async def test_delete_all_by_session(
    context_repository: ContextRepository, context_file
):
    """Test deleting all context files for a session."""
    await context_repository.delete_all_by_session(context_file.session_id)
    results = await context_repository.list_by_session(context_file.session_id)
    assert len(results) == 0


async def test_delete_by_session_and_id(
    context_repository: ContextRepository, context_file
):
    """Test deleting a context file by ID."""
    await context_repository.delete_by_session_and_id(
        context_file.session_id, context_file.id
    )
    result = await context_repository.get_by_session_and_path(
        context_file.session_id, context_file.file_path
    )
    assert result is None
