"""Dependency tests for the patches app."""

from unittest.mock import AsyncMock

from app.patches.dependencies import get_diff_patch_service


class TestPatchesDependencies:
    async def test_get_diff_patch_service_delegates_to_factory_and_returns_instance(
        self,
        mocker,
        diff_patch_service_mock,
    ):
        """Should await build_diff_patch_service() and return the same instance."""
        mocker.patch(
            "app.patches.dependencies.build_diff_patch_service",
            new=AsyncMock(return_value=diff_patch_service_mock),
        )
        _ = await get_diff_patch_service()
        pass

    async def test_get_diff_patch_service_propagates_factory_error(self, mocker):
        """Should surface exceptions from build_diff_patch_service."""
        mocker.patch(
            "app.patches.dependencies.build_diff_patch_service",
            new=AsyncMock(side_effect=ValueError("Boom")),
        )
        pass