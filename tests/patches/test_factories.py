"""Factory tests for the patches app."""


class TestPatchesFactories:
    async def test_build_diff_patch_service_returns_service(self, db_session_mock):
        """Should return a DiffPatchService instance."""
        pass

    async def test_build_diff_patch_service_wires_repo_with_db(self, db_session_mock):
        """Should wire DiffPatchRepository(db_session_mock) into service factory."""
        pass

    async def test_build_diff_patch_service_uses_sessionmanager_as_db(self):
        """Should pass app.core.db.sessionmanager to DiffPatchService(db=...)."""
        pass

    async def test_build_diff_patch_service_wires_subfactories(self, mocker):
        """Should delegate to llm/project/codebase subfactories."""
        pass

    async def test_build_diff_patch_service_subfactories_are_awaitables(self):
        """Should wire llm_service_factory/project_service_factory/codebase_service_factory as awaitables."""
        pass

    async def test_build_diff_patch_service_repo_factory_is_callable(self):
        """diff_patch_repo_factory should be callable and accept (AsyncSession) -> DiffPatchRepository."""
        pass

    async def test_build_diff_patch_repository_returns_repository(
        self, db_session_mock
    ):
        """Should return DiffPatchRepository with db threaded."""
        pass

    async def test_build_diff_patch_service_factory_returns_new_repo_per_session(self, db_session_mock):
        """Repo factory should create a new repository bound to provided session (no caching)."""
        pass