import pytest
from unittest.mock import AsyncMock

from app.llms.enums import LLMModel, LLMProvider, LLMRole
from app.llms.factories import build_llm_factory_instance
from app.llms.models import LLMSettings
from app.llms.services import LLMService
from app.llms.repositories import LLMSettingsRepository
from app.llms.schemas import LLM
from app.llms.registry import LLMFactory


def _fake_llm_model_name_for_provider(provider: LLMProvider) -> LLMModel:
    if provider == LLMProvider.OPENAI:
        return LLMModel.GPT_4O
    if provider == LLMProvider.ANTHROPIC:
        return LLMModel.CLAUDE_OPUS_4_1
    if provider == LLMProvider.GOOGLE:
        return LLMModel.GEMINI_2_5_FLASH
    raise ValueError(f"Unsupported provider in test fixture: {provider}")


@pytest.fixture(autouse=True)
async def _clear_llm_caches():
    build_llm_factory_instance.cache_clear()
    LLMService._get_client_instance.cache_clear()
    yield
    build_llm_factory_instance.cache_clear()
    LLMService._get_client_instance.cache_clear()


@pytest.fixture
async def llm_settings(db_session):
    obj = LLMSettings(
        model_name=LLMModel.GPT_4O,
        provider=LLMProvider.OPENAI,
        api_key="sk-openai",
        context_window=128000,
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
        active_role=None,
    )
    db_session.add(obj)
    await db_session.flush()
    return obj


@pytest.fixture
async def llm_settings_anthropic(db_session):
    obj = LLMSettings(
        model_name=LLMModel.CLAUDE_OPUS_4_1,
        provider=LLMProvider.ANTHROPIC,
        api_key="sk-anthropic",
        context_window=200000,
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
        active_role=None,
    )
    db_session.add(obj)
    await db_session.flush()
    return obj


@pytest.fixture
async def llm_settings_openai_coder(db_session):
    obj = LLMSettings(
        model_name=LLMModel.GPT_4O,
        provider=LLMProvider.OPENAI,
        api_key="sk-openai",
        context_window=128000,
        active_role=LLMRole.CODER,
    )
    db_session.add(obj)
    await db_session.flush()
    return obj


class FakeLLMFactory(LLMFactory):
    def __init__(self, model_registry: dict[LLMModel, LLM]):
        self._model_registry = model_registry

    async def get_llm(self, model_name: LLMModel) -> LLM:
        return self._model_registry[model_name]

    async def get_all_llms(self) -> list[LLM]:
        return list(self._model_registry.values())


@pytest.fixture
def fake_llm_client():
    client = AsyncMock()
    client.model = "fake-model"
    return client


@pytest.fixture
def make_llm_service_with_fake_factory(db_session):
    def _make(*, model_registry: dict[LLMModel, LLM]) -> LLMService:
        repo = LLMSettingsRepository(db_session)
        factory = FakeLLMFactory(model_registry=model_registry)
        return LLMService(repo, factory)

    return _make


@pytest.fixture
async def llm_service(db_session) -> LLMService:
    repo = LLMSettingsRepository(db_session)
    factory = await build_llm_factory_instance()
    return LLMService(repo, factory)


@pytest.fixture(autouse=True)
async def ensure_default_coder_llm_for_suite(db_session, request):
    """Ensure agents/settings that call llm_service.get_coding_llm() have a default model available.

    This is global because multiple apps assume at least one LLMSettings row exists.
    """
    # Skip for LLM unit tests to avoid unique constraint conflicts and pollution
    if "tests/llms" in str(request.node.fspath):
        yield
        return

    repo = LLMSettingsRepository(db_session)
    existing_coder = await repo.get_by_role(LLMRole.CODER)
    if existing_coder is None:
        existing_default = await repo.get_by_model_name(str(LLMModel.GPT_4_1_MINI))
        if existing_default is None:
            db_session.add(
                LLMSettings(
                    model_name=LLMModel.GPT_4_1_MINI,
                    provider=LLMProvider.OPENAI,
                    api_key="sk-test-openai",
                    context_window=128000,
                    active_role=LLMRole.CODER,
                )
            )
            await db_session.flush()
        else:
            await repo.set_active_role(llm_id=existing_default.id, role=LLMRole.CODER)
            await db_session.flush()
    yield
