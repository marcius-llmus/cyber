import pytest
import inspect
from app.llms import dependencies
from app.llms.services import LLMService


@pytest.mark.parametrize(
    "dependency_name",
    [
        "get_llm_service",
    ],
)
def test_llms_dependencies__module_exposes_expected_dependency_factories(dependency_name: str):
    """Covers: dependency surface. Asserts: llms.dependencies exposes expected providers."""
    assert hasattr(dependencies, dependency_name)


async def test_get_llm_service__returns_llm_service_instance(db_session_mock):
    """Scenario: resolve the llm service via dependency.

    Asserts:
        - returns an LLMService instance
        - service is wired to the provided AsyncSession
    """
    service = await dependencies.get_llm_service(db_session_mock)
    assert isinstance(service, LLMService)
    assert service.llm_settings_repo.db is db_session_mock


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
    mocker.patch("app.llms.dependencies.build_llm_service", side_effect=ValueError("Boom"))
    
    with pytest.raises(ValueError, match="Boom"):
        await dependencies.get_llm_service(db_session_mock)