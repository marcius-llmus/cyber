import pytest
from unittest.mock import AsyncMock
from app.llms.factories import build_llm_factory_instance, build_llm_service
from app.llms.services import LLMService
from app.llms.registry import LLMFactory
from app.llms.enums import LLMModel
from app.llms.schemas import LLM


async def test_build_llm_factory_instance__returns_llm_factory_singleton():
    """Scenario: calling build_llm_factory_instance multiple times.

    Asserts:
        - returns an LLMFactory
        - returns the same instance due to caching
    """
    # no mock here as we are checking for the real deal, cj! I am genius
    factory1 = await build_llm_factory_instance()
    factory2 = await build_llm_factory_instance()
    assert isinstance(factory1, LLMFactory)
    assert factory1 is factory2 # different from others. here, we WANT the same .-. (lru cached)


async def test_build_llm_service__returns_llm_service(db_session_mock, mocker, llm_factory_instance_mock):
    """Scenario: build_llm_service is called with a DB session.

    Asserts:
        - returns an LLMService instance
    """
    build_factory_instance_mock = mocker.patch(
        "app.llms.factories.build_llm_factory_instance",
        new=AsyncMock(return_value=llm_factory_instance_mock),
    )

    service = await build_llm_service(db_session_mock)
    assert isinstance(service, LLMService)
    build_factory_instance_mock.assert_awaited_once()


async def test_build_llm_service__wires_repository_and_factory(db_session_mock, mocker, llm_factory_instance_mock):
    """Scenario: build_llm_service builds all dependencies.

    Asserts:
        - service.llm_settings_repo is an LLMSettingsRepository bound to db_session_mock
        - service.llm_factory is an LLMFactory
    """
    build_factory_instance_mock = mocker.patch(
        "app.llms.factories.build_llm_factory_instance",
        new=AsyncMock(return_value=llm_factory_instance_mock),
    )

    service = await build_llm_service(db_session_mock)
    assert service.llm_settings_repo.db is db_session_mock
    assert service.llm_factory is llm_factory_instance_mock
    build_factory_instance_mock.assert_awaited_once()


async def test_build_llm_service__factory_is_cached_between_calls(db_session_mock, mocker, llm_factory_instance_mock):
    """Scenario: build_llm_service called multiple times.

    Asserts:
        - underlying LLMFactory instance is reused (cached)
        - repository instances are new per call (request-scoped)
    """
    build_factory_instance_mock = mocker.patch(
        "app.llms.factories.build_llm_factory_instance",
        new=AsyncMock(return_value=llm_factory_instance_mock),
    )

    service1 = await build_llm_service(db_session_mock)
    service2 = await build_llm_service(db_session_mock)

    assert service1.llm_factory is service2.llm_factory
    assert service1.llm_settings_repo is not service2.llm_settings_repo

    assert build_factory_instance_mock.await_count == 2


@pytest.mark.parametrize(
    "model_name",
    [
        LLMModel.GPT_4O,
        LLMModel.GPT_4_1_MINI,
        LLMModel.CLAUDE_SONNET_4_5,
        LLMModel.GEMINI_2_5_FLASH_LITE,
    ],
)
async def test_llm_factory__get_llm__returns_registry_entry(model_name: LLMModel):
    """Scenario: retrieving a known model from the registry.

    Asserts:
        - returns an LLM schema
        - returned model_name matches requested model_name
    """
    factory = LLMFactory()
    llm = await factory.get_llm(model_name)
    assert isinstance(llm, LLM)
    assert llm.model_name == model_name


async def test_llm_factory__get_all_llms__returns_all_registry_values():
    """Scenario: listing all models from the registry.

    Asserts:
        - returns a list of LLM schemas
        - list is non-empty
        - each item is an LLM schema
    """
    factory = LLMFactory()
    llms = await factory.get_all_llms()

    assert isinstance(llms, list)
    assert len(llms) > 0
    assert all(isinstance(item, LLM) for item in llms)