import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.llms.models import LLMSettings
from app.llms.enums import LLMRole, LLMProvider, LLMModel

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
