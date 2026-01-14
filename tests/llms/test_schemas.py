import pytest

from pydantic import ValidationError

from app.llms.enums import LLMModel, LLMProvider
from app.llms.schemas import LLM


def test_llm_schema__accepts_valid_payload():
    """Scenario: build LLM schema with valid enum values.

    Asserts:
        - model builds successfully
        - fields are accessible
    """
    model = LLM(
        model_name=LLMModel.GPT_4O,
        provider=LLMProvider.OPENAI,
        default_context_window=128_000,
    )

    assert model.model_name == LLMModel.GPT_4O
    assert model.provider == LLMProvider.OPENAI
    assert model.default_context_window == 128_000


@pytest.mark.parametrize(
    "field_name,bad_value",
    [
        ("model_name", "not-a-model"),
        ("provider", "not-a-provider"),
        ("default_context_window", "not-an-int"),
    ],
)
def test_llm_schema__rejects_invalid_field_types_or_values(field_name: str, bad_value):
    """Scenario: invalid payload per field.

    Asserts:
        - pydantic raises validation error
    """
    payload = {"model_name": LLMModel.GPT_4O, "provider": LLMProvider.OPENAI, "default_context_window": 128_000,
               field_name: bad_value}

    with pytest.raises(ValidationError):
        LLM(**payload)


@pytest.mark.parametrize(
    "value",
    [
        0,
        -1,
    ],
)
def test_llm_schema__default_context_window__rejects_non_positive(value: int):
    """Scenario: default_context_window must be a positive integer.

    Asserts:
        - pydantic raises validation error
    """
    with pytest.raises(ValidationError):
        LLM(model_name=LLMModel.GPT_4O, provider=LLMProvider.OPENAI, default_context_window=value)