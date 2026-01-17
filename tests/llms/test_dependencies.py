import inspect
from unittest.mock import AsyncMock

import pytest

from app.llms import dependencies


@pytest.mark.parametrize(
    "dependency_name",
    [
        "get_llm_service",
    ],
)
def test_llms_dependencies__module_exposes_expected_dependency_factories(dependency_name: str):
    """Covers: dependency surface. Asserts: llms.dependencies exposes expected providers."""
    assert hasattr(dependencies, dependency_name)


async def test_get_llm_service__returns_llm_service_instance(db_session_mock, mocker, llm_service_mock):
    """Scenario: resolve the llm service via dependency.

    Asserts:
        - delegates to build_llm_service(db=...)
        - returns the exact object returned by the factory
    """
    build_llm_service_mock = mocker.patch(
        "app.llms.dependencies.build_llm_service",
        new=AsyncMock(return_value=llm_service_mock),
    )

    service = await dependencies.get_llm_service(db_session_mock)

    assert service is llm_service_mock
    build_llm_service_mock.assert_awaited_once_with(db_session_mock)


def test_get_llm_service__is_async_dependency():
    """Scenario: get_llm_service is used as a FastAPI dependency.

    Asserts:
        - the dependency callable is declared async
    """
    assert inspect.iscoroutinefunction(dependencies.get_llm_service)


async def test_get_llm_service__propagates_factory_errors(db_session_mock, mocker):
    """Scenario: underlying build_llm_service raises.

    Asserts:
        - the exception propagates (dependency does not swallow)
    """
    build_llm_service_mock = mocker.patch(
        "app.llms.dependencies.build_llm_service",
        new=AsyncMock(side_effect=ValueError("Boom")),
    )

    with pytest.raises(ValueError, match="Boom"):
        await dependencies.get_llm_service(db_session_mock)

    build_llm_service_mock.assert_awaited_once_with(db_session_mock)
