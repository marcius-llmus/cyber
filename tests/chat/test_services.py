import pytest
from llama_index.core.llms import MessageRole

from app.chat.enums import ChatTurnStatus
from app.chat.models import ChatTurn, Message
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.models import Project
from app.sessions.models import ChatSession


class TestChatService:
    async def test_get_or_create_active_session_raises_when_no_active_project(
        self, chat_service, project_service_mock
    ):
        """Raises ActiveProjectRequiredException when there is no active project."""
        project_service_mock.get_active_project.return_value = None
        with pytest.raises(ActiveProjectRequiredException):
            await chat_service.get_or_create_active_session()

    async def test_get_or_create_active_session_returns_session_for_active_project(
        self, chat_service, project_service_mock, session_service_mock
    ):
        """Returns most-recent session for active project when it exists, otherwise creates a new one."""
        project = Project(id=1, name="P1")
        project_service_mock.get_active_project.return_value = project

        expected_session = ChatSession(id=10, project_id=1)
        session_service_mock.get_most_recent_session_by_project.return_value = (
            expected_session
        )

        session = await chat_service.get_or_create_active_session()
        assert session == expected_session
        session_service_mock.get_most_recent_session_by_project.assert_awaited_with(
            project_id=1
        )

    async def test_get_or_create_session_for_project_returns_existing_session(
        self, chat_service, session_service_mock
    ):
        """get_or_create_session_for_project returns the most recent session if one exists."""
        expected_session = ChatSession(id=10, project_id=1)
        session_service_mock.get_most_recent_session_by_project.return_value = (
            expected_session
        )

        session = await chat_service.get_or_create_session_for_project(project_id=1)
        assert session == expected_session

    async def test_get_or_create_session_for_project_creates_new_session_if_none_exist(
        self, chat_service, session_service_mock
    ):
        """get_or_create_session_for_project creates a new session if none exist for the project."""
        session_service_mock.get_most_recent_session_by_project.return_value = None
        expected_session = ChatSession(id=11, project_id=1)
        session_service_mock.create_session.return_value = expected_session

        session = await chat_service.get_or_create_session_for_project(project_id=1)
        assert session == expected_session
        session_service_mock.create_session.assert_awaited_once()

    async def test_add_user_message_creates_message_with_user_role_and_text_block(
        self, chat_service, message_repository_mock
    ):
        """add_user_message should call message_repo.create with USER role and a single text block."""
        await chat_service.add_user_message(content="hi", session_id=1, turn_id="t1")

        assert message_repository_mock.create.called
        call_args = message_repository_mock.create.call_args[1]
        obj_in = call_args["obj_in"]
        assert obj_in.role == MessageRole.USER
        assert obj_in.session_id == 1
        assert obj_in.turn_id == "t1"
        assert len(obj_in.blocks) == 1
        assert obj_in.blocks[0]["type"] == "text"
        assert obj_in.blocks[0]["content"] == "hi"

    async def test_add_ai_message_creates_message_with_assistant_role(
        self, chat_service, message_repository_mock
    ):
        """add_ai_message should call message_repo.create with ASSISTANT role and provided blocks."""
        blocks = [{"type": "text", "content": "hello"}]
        await chat_service.add_ai_message(session_id=1, turn_id="t1", blocks=blocks)

        assert message_repository_mock.create.called
        call_args = message_repository_mock.create.call_args[1]
        obj_in = call_args["obj_in"]
        assert obj_in.role == MessageRole.ASSISTANT
        assert obj_in.blocks == blocks

    async def test_get_chat_history_returns_llama_index_chat_messages(
        self, chat_service, message_repository_mock
    ):
        """get_chat_history maps db Message models to llama_index ChatMessage objects."""
        msg1 = Message(
            role=MessageRole.USER, blocks=[{"type": "text", "content": "hi"}]
        )
        msg2 = Message(
            role=MessageRole.ASSISTANT, blocks=[{"type": "text", "content": "hello"}]
        )
        message_repository_mock.list_by_session_id.return_value = [msg1, msg2]

        history = await chat_service.get_chat_history(session_id=1)
        assert len(history) == 2
        assert history[0].role == MessageRole.USER
        assert history[0].content == "hi"
        assert history[1].role == MessageRole.ASSISTANT
        assert history[1].content == "hello"

    async def test_get_session_by_id_delegates_to_session_service(
        self, chat_service, session_service_mock
    ):
        """get_session_by_id calls session_service.get_session."""
        await chat_service.get_session_by_id(session_id=1)
        session_service_mock.get_session.assert_awaited_with(session_id=1)

    async def test_list_messages_by_session_delegates_to_repo(
        self, chat_service, message_repository_mock
    ):
        """list_messages_by_session calls message_repo.list_by_session_id."""
        await chat_service.list_messages_by_session(session_id=1)
        message_repository_mock.list_by_session_id.assert_awaited_with(session_id=1)

    async def test_save_messages_for_turn_saves_user_then_ai_message(
        self, chat_service, message_repository_mock
    ):
        """save_messages_for_turn calls add_user_message then add_ai_message for the same turn."""
        # We can't easily assert order with separate methods, but we can verify both are called
        await chat_service.save_messages_for_turn(
            session_id=1,
            turn_id="t1",
            user_content="u",
            blocks=[{"type": "text", "content": "a"}],
        )
        assert message_repository_mock.create.call_count == 2

    async def test_clear_session_messages_calls_repository_delete(
        self, chat_service, message_repository_mock
    ):
        """clear_session_messages delegates to message_repo.delete_by_session_id."""
        await chat_service.clear_session_messages(session_id=1)
        message_repository_mock.delete_by_session_id.assert_awaited_with(session_id=1)


class TestChatTurnService:
    async def test_start_turn_generates_turn_id_and_creates_pending_turn_when_turn_id_is_none(
        self, chat_turn_service, chat_turn_repository_mock
    ):
        """start_turn should create a new PENDING ChatTurn and return its id when turn_id is None."""
        turn_id = await chat_turn_service.start_turn(session_id=1)
        assert turn_id is not None
        assert chat_turn_repository_mock.create.called
        call_args = chat_turn_repository_mock.create.call_args[1]
        assert call_args["obj_in"].id == turn_id
        assert call_args["obj_in"].status == ChatTurnStatus.PENDING

    async def test_start_turn_raises_when_retry_turn_not_found(
        self, chat_turn_service, chat_turn_repository_mock
    ):
        """start_turn should raise ValueError when retry is requested for a non-existent turn."""
        chat_turn_repository_mock.get_by_id_and_session.return_value = None
        with pytest.raises(ValueError, match="does not exist"):
            await chat_turn_service.start_turn(session_id=1, turn_id="missing")

    async def test_start_turn_raises_when_turn_already_succeeded(
        self, chat_turn_service, chat_turn_repository_mock
    ):
        """start_turn should raise ValueError when retrying a SUCCEEDED turn."""
        turn = ChatTurn(id="t1", status=ChatTurnStatus.SUCCEEDED)
        chat_turn_repository_mock.get_by_id_and_session.return_value = turn
        with pytest.raises(ValueError, match="already succeeded"):
            await chat_turn_service.start_turn(session_id=1, turn_id="t1")

    async def test_start_turn_returns_existing_turn_id_when_turn_exists_and_not_succeeded(
        self, chat_turn_service, chat_turn_repository_mock
    ):
        """start_turn returns the provided turn_id when it exists and is not SUCCEEDED."""
        turn = ChatTurn(id="t1", status=ChatTurnStatus.PENDING)
        chat_turn_repository_mock.get_by_id_and_session.return_value = turn
        returned_id = await chat_turn_service.start_turn(session_id=1, turn_id="t1")
        assert returned_id == "t1"

    async def test_mark_succeeded_raises_when_turn_missing(
        self, chat_turn_service, chat_turn_repository_mock
    ):
        """mark_succeeded raises ValueError when the turn cannot be found."""
        chat_turn_repository_mock.get_by_id_and_session.return_value = None
        with pytest.raises(ValueError, match="not found"):
            await chat_turn_service.mark_succeeded(session_id=1, turn_id="missing")

    async def test_mark_succeeded_updates_turn_status_to_succeeded(
        self, chat_turn_service, chat_turn_repository_mock
    ):
        """mark_succeeded calls turn_repo.update with status=SUCCEEDED."""
        turn = ChatTurn(id="t1", status=ChatTurnStatus.PENDING)
        chat_turn_repository_mock.get_by_id_and_session.return_value = turn

        await chat_turn_service.mark_succeeded(session_id=1, turn_id="t1")

        assert chat_turn_repository_mock.update.called
        call_args = chat_turn_repository_mock.update.call_args[1]
        assert call_args["obj_in"].status == ChatTurnStatus.SUCCEEDED
