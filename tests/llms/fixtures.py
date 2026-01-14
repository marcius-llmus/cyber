import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.llms.models import LLMSettings
from app.llms.enums import LLMRole, LLMProvider, LLMModel
from app.llms.factories import build_llm_service


@pytest.fixture(autouse=True)
def _clear_llm_caches():
    """Clear async LRU caches to keep tests order-independent."""
    from app.llms.factories import build_llm_factory_instance
    from app.llms.services import LLMService

    build_llm_factory_instance.cache_clear()
    LLMService._get_client_instance.cache_clear()  # type: ignore[attr-defined]
    yield
    build_llm_factory_instance.cache_clear()
    LLMService._get_client_instance.cache_clear()  # type: ignore[attr-defined]


@pytest.fixture
async def llm_service(db_session: AsyncSession):
    return await build_llm_service(db_session)


@pytest.fixture
async def llm_settings(db_session: AsyncSession) -> LLMSettings:
    llm = LLMSettings(
        id=1,
        model_name=LLMModel.GPT_4O,
        provider=LLMProvider.OPENAI,
        api_key="sk-test",
        context_window=128000,
        active_role=LLMRole.CODER,
    )
    db_session.add(llm)
    await db_session.flush()
    await db_session.refresh(llm)
    return llm


@pytest.fixture
async def llm_settings_openai_no_role(db_session: AsyncSession) -> LLMSettings:
    llm = LLMSettings(
        model_name=LLMModel.GPT_4_1_MINI,
        provider=LLMProvider.OPENAI,
        api_key="sk-openai",
        context_window=128000,
        active_role=None,
    )
    db_session.add(llm)
    await db_session.flush()
    await db_session.refresh(llm)
    return llm


@pytest.fixture
async def llm_settings_openai_coder(db_session: AsyncSession) -> LLMSettings:
    llm = LLMSettings(
        model_name=LLMModel.GPT_4_1_MINI,
        provider=LLMProvider.OPENAI,
        api_key="sk-openai",
        context_window=128000,
        active_role=LLMRole.CODER,
    )
    db_session.add(llm)
    await db_session.flush()
    await db_session.refresh(llm)
    return llm


@pytest.fixture
async def llm_settings_anthropic(db_session: AsyncSession) -> LLMSettings:
    llm = LLMSettings(
        model_name=LLMModel.CLAUDE_SONNET_4_5,
        provider=LLMProvider.ANTHROPIC,
        api_key="sk-anthropic",
        context_window=200000,
        active_role=None,
    )
    db_session.add(llm)
    await db_session.flush()
    await db_session.refresh(llm)
    return llm


@pytest.fixture
async def llm_settings_google(db_session: AsyncSession) -> LLMSettings:
    llm = LLMSettings(
        model_name=LLMModel.GEMINI_2_5_FLASH_LITE,
        provider=LLMProvider.GOOGLE,
        api_key="sk-google",
        context_window=128000,
        active_role=None,
    )
    db_session.add(llm)
    await db_session.flush()
    await db_session.refresh(llm)
    return llm