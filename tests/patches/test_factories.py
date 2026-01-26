"""Factory tests for the patches app."""


class TestPatchesFactories:
    async def test_build_diff_patch_service_returns_service(self, db_session_mock):
        """Should return a DiffPatchService instance."""
        pass

    async def test_build_diff_patch_service_wires_repo_with_db(self, db_session_mock):
        """Should wire DiffPatchRepository(db_session_mock) into service factory."""
        pass

    async def test_build_diff_patch_service_wires_subfactories(self, mocker):
        """Should delegate to llm/project/codebase subfactories."""
        pass

    async def test_build_diff_patch_repository_returns_repository(
        self, db_session_mock
    ):
        """Should return DiffPatchRepository with db threaded."""
        pass
