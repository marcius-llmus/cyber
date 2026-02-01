from sqlalchemy import select

from app.llms.enums import LLMModel
from app.llms.models import LLMSettings
from app.settings.utils import initialize_application_settings


# todo: since it is a small func that uses repo directly, let's keep db session mock
#       but once we change it to use a service method, we shall update with mocks
async def test_initialize_application_settings_populates_reasoning_config(db_session):
    # Run initialization
    await initialize_application_settings(db_session)

    # Pick a model that we know has reasoning config, e.g. CLAUDE_SONNET_4_5
    stmt = select(LLMSettings).where(
        LLMSettings.model_name == LLMModel.CLAUDE_SONNET_4_5
    )
    result = await db_session.execute(stmt)
    llm_setting = result.scalar_one_or_none()

    assert llm_setting is not None
    assert llm_setting.reasoning_config is not None
    assert llm_setting.reasoning_config == {"type": "enabled", "budget_tokens": 8000}

    # Check another one, e.g. GPT_4_1_MINI
    stmt = select(LLMSettings).where(LLMSettings.model_name == LLMModel.GPT_4_1_MINI)
    result = await db_session.execute(stmt)
    llm_setting = result.scalar_one_or_none()

    assert llm_setting is not None
    assert llm_setting.reasoning_config == {"reasoning_effort": "medium"}
