"""Factory tests for the patches app."""

from unittest.mock import AsyncMock

import pytest

from app.context.services import CodebaseService
from app.llms.services import LLMService
from app.patches.factories import build_diff_patch_repository, build_diff_patch_service
from app.patches.repositories import DiffPatchRepository
from app.patches.services import DiffPatchService
from app.projects.services import ProjectService


class TestPatchesFactories:
    async def test_build_diff_patch_service_returns_service(self, db_session_mock):
        """Should return a DiffPatchService instance."""
        service = await build_diff_patch_service()
        assert isinstance(service, DiffPatchService)

    async def test_build_diff_patch_service_wires_repo_with_db(self, db_session_mock):
        """Should wire DiffPatchRepository(db_session_mock) into service factory."""
        service = await build_diff_patch_service()
        repo = service.diff_patch_repo_factory(db_session_mock)

        assert isinstance(repo, DiffPatchRepository)
        assert repo.db is db_session_mock

    async def test_build_diff_patch_service_uses_sessionmanager_as_db(self):
        """Should pass app.core.db.sessionmanager to DiffPatchService(db=...)."""
        from app.core.db import sessionmanager

        service = await build_diff_patch_service()
        assert service.db is sessionmanager

    async def test_build_diff_patch_service_wires_subfactories(self, mocker):
        """Should delegate to llm/project/codebase subfactories."""
        build_llm_service_mock = mocker.patch(
            "app.patches.factories.build_llm_service",
            new=AsyncMock(),
        )
        build_project_service_mock = mocker.patch(
            "app.patches.factories.build_project_service",
            new=AsyncMock(),
        )
        build_codebase_service_mock = mocker.patch(
            "app.patches.factories.build_codebase_service",
            new=AsyncMock(),
        )

        service = await build_diff_patch_service()

        assert service.llm_service_factory is build_llm_service_mock
        assert service.project_service_factory is build_project_service_mock
        assert service.codebase_service_factory is build_codebase_service_mock

    async def test_build_diff_patch_service_subfactories_are_awaitables(self):
        """Should wire llm_service_factory/project_service_factory/codebase_service_factory as awaitables."""
        service = await build_diff_patch_service()

        assert callable(service.llm_service_factory)
        assert callable(service.project_service_factory)
        assert callable(service.codebase_service_factory)

    async def test_build_diff_patch_service_repo_factory_is_callable(self):
        """diff_patch_repo_factory should be callable and accept (AsyncSession) -> DiffPatchRepository."""
        service = await build_diff_patch_service()

        assert callable(service.diff_patch_repo_factory)

    async def test_build_diff_patch_repository_returns_repository(
        self, db_session_mock
    ):
        """Should return DiffPatchRepository with db threaded."""
        repo = build_diff_patch_repository(db_session_mock)
        assert isinstance(repo, DiffPatchRepository)
        assert repo.db is db_session_mock

    async def test_build_diff_patch_service_factory_returns_new_repo_per_session(
        self, db_session_mock
    ):
        """Repo factory should create a new repository bound to provided session (no caching)."""
        service = await build_diff_patch_service()
        repo1 = service.diff_patch_repo_factory(db_session_mock)
        repo2 = service.diff_patch_repo_factory(db_session_mock)

        assert repo1 is not repo2

    async def test_build_diff_patch_service_factories_return_expected_types(
        self,
        mocker,
        llm_service_mock,
        project_service_mock,
        codebase_service_mock,
        db_session_mock,
    ):
        """Smoke-test that the wired factories are awaitables producing expected service types."""

        mocker.patch(
            "app.patches.factories.build_llm_service",
            new=AsyncMock(return_value=llm_service_mock),
        )
        mocker.patch(
            "app.patches.factories.build_project_service",
            new=AsyncMock(return_value=project_service_mock),
        )
        mocker.patch(
            "app.patches.factories.build_codebase_service",
            new=AsyncMock(return_value=codebase_service_mock),
        )

        service = await build_diff_patch_service()

        assert await service.llm_service_factory(db_session_mock) is llm_service_mock
        assert (
            await service.project_service_factory(db_session_mock)
            is project_service_mock
        )
        assert await service.codebase_service_factory() is codebase_service_mock

        assert isinstance(llm_service_mock, LLMService)
        assert isinstance(project_service_mock, ProjectService)
        assert isinstance(codebase_service_mock, CodebaseService)

    async def test_build_diff_patch_service_propagates_repo_factory_errors(
        self, mocker, db_session_mock
    ):
        """If repository constructor errors, the factory should surface it."""

        repo_cls_mock = mocker.patch(
            "app.patches.factories.DiffPatchRepository",
            side_effect=ValueError("Boom"),
        )

        with pytest.raises(ValueError, match="Boom"):
            _ = build_diff_patch_repository(db_session_mock)

        repo_cls_mock.assert_called_once_with(db_session_mock)