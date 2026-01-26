"""Dependency tests for the patches app."""

import inspect
from unittest.mock import AsyncMock

import pytest

from app.patches.dependencies import get_diff_patch_service


class TestPatchesDependencies:
    async def test_get_diff_patch_service_is_async_dependency(self):
        """get_diff_patch_service remains an async dependency (coroutine function)."""
        assert inspect.iscoroutinefunction(get_diff_patch_service)

    async def test_get_diff_patch_service_delegates_to_factory_and_returns_instance(
        self,
        mocker,
        diff_patch_service_mock,
    ):
        """Should await build_diff_patch_service() and return the same instance."""
        build_diff_patch_service_mock = mocker.patch(
            "app.patches.dependencies.build_diff_patch_service",
            new=AsyncMock(return_value=diff_patch_service_mock),
        )
        service = await get_diff_patch_service()

        assert service is diff_patch_service_mock
        build_diff_patch_service_mock.assert_awaited_once_with()

    async def test_get_diff_patch_service_propagates_factory_error(self, mocker):
        """Should surface exceptions from build_diff_patch_service."""
        build_diff_patch_service_mock = mocker.patch(
            "app.patches.dependencies.build_diff_patch_service",
            new=AsyncMock(side_effect=ValueError("Boom")),
        )

        with pytest.raises(ValueError, match="Boom"):
            await get_diff_patch_service()

        build_diff_patch_service_mock.assert_awaited_once_with()
