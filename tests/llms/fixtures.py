from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from app.llms.dependencies import get_llm_service
from app.llms.enums import LLMModel, LLMProvider, LLMRole
from app.llms.factories import build_llm_factory_instance
from app.llms.models import LLMSettings
from app.llms.registry import LLMFactory
from app.llms.repositories import LLMSettingsRepository
from app.llms.services import LLMService


def _fake_llm_model_name_for_provider(provider: LLMProvider) -> LLMModel:
    if provider == LLMProvider.OPENAI:
        return LLMModel.GPT_4_1
    if provider == LLMProvider.ANTHROPIC:
        return LLMModel.CLAUDE_OPUS_4_5
    if provider == LLMProvider.GOOGLE:
        return LLMModel.GEMINI_2_5_FLASH
    raise ValueError(f"Unsupported provider in test fixture: {provider}")


@pytest.fixture
async def llm_settings(db_session):
    obj = LLMSettings(
        model_name=LLMModel.GPT_4_1,
        provider=LLMProvider.OPENAI,
        api_key="sk-openai",
        context_window=128000,
        visual_name="GPT-4.1",
        active_role=None,
    )
    db_session.add(obj)
    await db_session.flush()
    return obj


@pytest.fixture
async def llm_settings_openai_no_role(db_session):
    obj = LLMSettings(
        model_name=LLMModel.GPT_4_1_MINI,
        provider=LLMProvider.OPENAI,
        api_key="sk-openai",
        context_window=128000,
        visual_name="GPT-4.1 Mini",
        active_role=None,
    )
    db_session.add(obj)
    await db_session.flush()
    return obj


@pytest.fixture
async def llm_settings_anthropic(db_session):
    obj = LLMSettings(
        model_name=LLMModel.CLAUDE_OPUS_4_5,
        provider=LLMProvider.ANTHROPIC,
        api_key="sk-anthropic",
        context_window=200000,
        visual_name="Claude 4.5 Opus",
        active_role=None,
    )
    db_session.add(obj)
    await db_session.flush()
    return obj


@pytest.fixture
async def llm_settings_google(db_session):
    obj = LLMSettings(
        model_name=LLMModel.GEMINI_2_5_FLASH,
        provider=LLMProvider.GOOGLE,
        api_key="sk-google",
        context_window=1000000,
        visual_name="Gemini 2.5 Flash",
        active_role=None,
    )
    db_session.add(obj)
    await db_session.flush()
    return obj


@pytest.fixture
async def llm_settings_openai_coder(db_session):
    obj = LLMSettings(
        model_name=LLMModel.GPT_4_1,
        provider=LLMProvider.OPENAI,
        api_key="sk-openai",
        context_window=128000,
        visual_name="GPT-4.1",
        active_role=LLMRole.CODER,
    )
    db_session.add(obj)
    await db_session.flush()
    return obj


@pytest.fixture
def fake_llm_client():
    client = AsyncMock()
    client.model = "fake-model"
    return client


@pytest.fixture
def llm_settings_repository(db_session) -> LLMSettingsRepository:
    return LLMSettingsRepository(db_session)


@pytest.fixture
def llm_settings_repository_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(LLMSettingsRepository, instance=True)


@pytest.fixture
async def llm_service(llm_settings_repository_mock: MagicMock) -> LLMService:
    """Provides a LLMService instance with a MOCKED repository for unit testing."""
    factory = await build_llm_factory_instance()
    return LLMService(llm_settings_repository_mock, factory)


@pytest.fixture
def llm_service_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(LLMService, instance=True)


@pytest.fixture
def llm_factory_instance() -> LLMFactory:
    return LLMFactory()


@pytest.fixture
def llm_factory_instance_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.create_autospec(LLMFactory, instance=True)


@pytest.fixture
def override_get_llm_service(client, llm_service_mock: MagicMock):
    client.app.dependency_overrides[get_llm_service] = lambda: llm_service_mock
    yield
    client.app.dependency_overrides.clear()


@pytest.fixture
def llm_settings_coder_mock() -> LLMSettings:
    return LLMSettings(
        id=100,
        model_name=LLMModel.GPT_4_1,
        provider=LLMProvider.OPENAI,
        api_key="sk-openai",
        context_window=128000,
        visual_name="GPT-4.1",
        active_role=LLMRole.CODER,
    )


@pytest.fixture
async def llm_settings_seed_many(db_session) -> list[LLMSettings]:
    rows = [
        LLMSettings(
            model_name=LLMModel.GPT_4_1_MINI,
            provider=LLMProvider.OPENAI,
            api_key="sk-openai",
            context_window=128000,
            visual_name="GPT-4.1 Mini",
            active_role=LLMRole.CODER,
        ),
        LLMSettings(
            model_name=LLMModel.CLAUDE_OPUS_4_5,
            provider=LLMProvider.ANTHROPIC,
            api_key="sk-anthropic",
            context_window=200000,
            visual_name="Claude 4.5 Opus",
            active_role=None,
        ),
        LLMSettings(
            model_name=LLMModel.GEMINI_2_5_FLASH,
            provider=LLMProvider.GOOGLE,
            api_key="sk-google",
            context_window=1000000,
            visual_name="Gemini 2.5 Flash",
            active_role=None,
        ),
    ]
    db_session.add_all(rows)
    await db_session.flush()
    return rows


@pytest.fixture
def llm_settings_mock() -> LLMSettings:
    return LLMSettings(
        id=1,
        model_name=LLMModel.GPT_4_1,
        provider=LLMProvider.OPENAI,
        api_key="sk-openai",
        context_window=128000,
        visual_name="GPT-4.1",
        active_role=None,
    )


@pytest.fixture
def llm_settings_openai_no_role_mock() -> LLMSettings:
    return LLMSettings(
        id=2,
        model_name=LLMModel.GPT_4_1_MINI,
        provider=LLMProvider.OPENAI,
        api_key="sk-openai",
        context_window=128000,
        visual_name="GPT-4.1 Mini",
        active_role=None,
    )


@pytest.fixture
def llm_settings_anthropic_mock() -> LLMSettings:
    return LLMSettings(
        id=3,
        model_name=LLMModel.CLAUDE_OPUS_4_5,
        provider=LLMProvider.ANTHROPIC,
        api_key="sk-anthropic",
        context_window=200000,
        visual_name="Claude 4.5 Opus",
        active_role=None,
    )


@pytest.fixture
def llm_settings_openai_coder_mock() -> LLMSettings:
    return LLMSettings(
        id=4,
        model_name=LLMModel.GPT_4_1,
        provider=LLMProvider.OPENAI,
        api_key="sk-openai",
        context_window=128000,
        visual_name="GPT-4.1",
        active_role=LLMRole.CODER,
    )


@pytest.fixture
def llm_settings_seed_many_mock() -> list[LLMSettings]:
    return [
        LLMSettings(
            id=10,
            model_name=LLMModel.GPT_4_1_MINI,
            provider=LLMProvider.OPENAI,
            api_key="sk-openai",
            context_window=128000,
            visual_name="GPT-4.1 Mini",
            active_role=LLMRole.CODER,
        ),
        LLMSettings(
            id=11,
            model_name=LLMModel.CLAUDE_OPUS_4_5,
            provider=LLMProvider.ANTHROPIC,
            api_key="sk-anthropic",
            context_window=200000,
            visual_name="Claude 4.5 Opus",
            active_role=None,
        ),
        LLMSettings(
            id=12,
            model_name=LLMModel.GEMINI_2_5_FLASH,
            provider=LLMProvider.GOOGLE,
            api_key="sk-google",
            context_window=1000000,
            visual_name="Gemini 2.5 Flash",
            active_role=None,
        ),
    ]
