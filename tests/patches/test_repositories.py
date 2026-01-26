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

    async def test_list_by_turn_filters_and_orders(
        self,
        diff_patch_repository,
        db_session,
        chat_session,
    ):
        """Should return all patches for given (session_id, turn_id) ordered by created_at asc."""
        pass
