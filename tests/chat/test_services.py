"""Service tests for the chat app.

Skeleton-only: implement assertions later.

NOTE: Service tests must NOT use db_session. Mock repositories instead.
"""


class TestChatService:
    async def test_get_or_create_active_session_raises_when_no_active_project(self):
        """Raises ActiveProjectRequiredException when there is no active project."""
        pass

    async def test_get_or_create_active_session_returns_session_for_active_project(self):
        """Returns most-recent session for active project when it exists, otherwise creates a new one."""
        pass

    async def test_get_or_create_session_for_project_returns_existing_session(self):
        """get_or_create_session_for_project returns the most recent session if one exists."""
        pass

    async def test_get_or_create_session_for_project_creates_new_session_if_none_exist(self):
        """get_or_create_session_for_project creates a new session if none exist for the project."""
        pass

    async def test_add_user_message_creates_message_with_user_role_and_text_block(self):
        """add_user_message should call message_repo.create with USER role and a single text block."""
        pass

    async def test_add_ai_message_creates_message_with_assistant_role(self):
        """add_ai_message should call message_repo.create with ASSISTANT role and provided blocks."""
        pass

    async def test_get_chat_history_returns_llama_index_chat_messages(self):
        """get_chat_history maps db Message models to llama_index ChatMessage objects."""
        pass

    async def test_get_session_by_id_delegates_to_session_service(self):
        """get_session_by_id calls session_service.get_session."""
        pass

    async def test_list_messages_by_session_delegates_to_repo(self):
        """list_messages_by_session calls message_repo.list_by_session_id."""
        pass

    async def test_save_messages_for_turn_saves_user_then_ai_message(self):
        """save_messages_for_turn calls add_user_message then add_ai_message for the same turn."""
        pass

    async def test_clear_session_messages_calls_repository_delete(self):
        """clear_session_messages delegates to message_repo.delete_by_session_id."""
        pass


class TestChatTurnService:
    async def test_start_turn_generates_turn_id_and_creates_pending_turn_when_turn_id_is_none(self):
        """start_turn should create a new PENDING ChatTurn and return its id when turn_id is None."""
        pass

    async def test_start_turn_raises_when_retry_turn_not_found(self):
        """start_turn should raise ValueError when retry is requested for a non-existent turn."""
        pass

    async def test_start_turn_raises_when_turn_already_succeeded(self):
        """start_turn should raise ValueError when retrying a SUCCEEDED turn."""
        pass

    async def test_start_turn_returns_existing_turn_id_when_turn_exists_and_not_succeeded(self):
        """start_turn returns the provided turn_id when it exists and is not SUCCEEDED."""
        pass

    async def test_mark_succeeded_raises_when_turn_missing(self):
        """mark_succeeded raises ValueError when the turn cannot be found."""
        pass

    async def test_mark_succeeded_updates_turn_status_to_succeeded(self):
        """mark_succeeded calls turn_repo.update with status=SUCCEEDED."""
        pass