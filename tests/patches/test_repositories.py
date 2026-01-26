"""Repository tests for the patches app."""


class TestDiffPatchRepository:
    async def test_list_pending_by_turn_filters_and_orders(
        self,
        diff_patch_repository,
        db_session,
        chat_session,
    ):
        """Should return only PENDING patches for given (session_id, turn_id) ordered by created_at asc."""
        pass

    async def test_list_pending_by_turn_excludes_non_pending_statuses(
        self,
        diff_patch_repository,
        db_session,
        chat_session,
    ):
        """Should exclude APPLIED/FAILED/REJECTED patches even if turn_id matches."""
        pass

    async def test_list_pending_by_turn_excludes_other_turns_and_sessions(
        self,
        diff_patch_repository,
        db_session,
        chat_session,
    ):
        """Should only return rows for the exact (session_id, turn_id)."""
        pass

    async def test_list_by_turn_filters_and_orders(
        self,
        diff_patch_repository,
        db_session,
        chat_session,
    ):
        """Should return all patches for given (session_id, turn_id) ordered by created_at asc."""
        pass

    async def test_list_by_turn_returns_empty_when_none(self, diff_patch_repository):
        """Should return [] when there are no patches for given (session_id, turn_id)."""
        pass