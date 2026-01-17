import pytest
from sqlalchemy.exc import IntegrityError

from app.llms.enums import LLMModel, LLMProvider, LLMRole
from app.llms.models import LLMSettings


async def test_llm_settings__can_be_persisted(db_session):
    """Scenario: create + flush an LLMSettings row.

    Asserts:
        - row is persisted and retrievable by primary key
        - required fields are stored
    """
    obj = LLMSettings(
        model_name=LLMModel.GPT_4O,
        provider=LLMProvider.OPENAI,
        api_key="sk-test",
        context_window=128000,
        active_role=None,
    )
    db_session.add(obj)
    await db_session.flush()
    assert obj.id is not None


@pytest.mark.parametrize(
    "field_name",
    [
        "model_name",
        "provider",
        "context_window",
    ],
)
async def test_llm_settings__required_fields__enforced_by_db(
    field_name: str, db_session
):
    """Scenario: attempt to persist LLMSettings with a missing required field.

    Asserts:
        - DB raises integrity error for nullable=False columns
    """
    valid_data = {
        "model_name": LLMModel.GPT_4O,
        "provider": LLMProvider.OPENAI,
        "context_window": 128000,
    }
    valid_data.pop(field_name)
    llm = LLMSettings(**valid_data)
    db_session.add(llm)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_llm_settings__model_name_unique(db_session):
    """Scenario: insert two rows with same model_name.

    Asserts:
        - DB unique constraint rejects duplicates
    """
    first = LLMSettings(
        model_name=LLMModel.GPT_4O,
        provider=LLMProvider.OPENAI,
        context_window=128000,
    )
    db_session.add(first)
    await db_session.flush()

    second = LLMSettings(
        model_name=LLMModel.GPT_4O,
        provider=LLMProvider.OPENAI,
        context_window=128000,
    )
    db_session.add(second)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_llm_settings__active_role_unique(db_session):
    """Scenario: insert two rows with same active_role (e.g., CODER).

    Asserts:
        - DB unique constraint rejects duplicates
    """
    first = LLMSettings(
        model_name=LLMModel.GPT_4O,
        provider=LLMProvider.OPENAI,
        context_window=128000,
        active_role=LLMRole.CODER,
    )
    db_session.add(first)
    await db_session.flush()

    second = LLMSettings(
        model_name=LLMModel.GPT_4_TURBO,
        provider=LLMProvider.OPENAI,
        context_window=128000,
        active_role=LLMRole.CODER,
    )
    db_session.add(second)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_llm_settings__api_key_nullable(db_session):
    """Scenario: persist an LLMSettings row with api_key=None.

    Asserts:
        - row persists successfully
    """
    llm = LLMSettings(
        model_name=LLMModel.GPT_4O,
        provider=LLMProvider.OPENAI,
        api_key=None,
        context_window=128000,
    )
    db_session.add(llm)
    await db_session.flush()
    assert llm.id is not None
