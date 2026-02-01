from unittest.mock import AsyncMock

import pytest
from google.genai import types

from app.llms.enums import LLMModel, LLMProvider
from app.llms.schemas import LLM
from app.llms.services import LLMService


@pytest.fixture
def mock_llm_factory():
    return AsyncMock()


@pytest.fixture
def mock_llm_settings_repo():
    return AsyncMock()


@pytest.fixture
def llm_service(mock_llm_settings_repo, mock_llm_factory):
    return LLMService(mock_llm_settings_repo, mock_llm_factory)


@pytest.mark.asyncio
async def test_get_client_instance__google_gemini_3__passes_thinking_config(
    llm_service, mocker
):
    """
    Scenario: Requesting a client for Gemini 3 (which supports thinking).
    Expected: thinking_config is included in generation_config.
    """
    # Arrange
    model_name = LLMModel.GEMINI_3_FLASH
    provider = LLMProvider.GOOGLE
    temperature = 0.7
    api_key = "fake-key"
    reasoning_config = (("thinking_level", "LOW"),)

    mock_llm = LLM(
        model_name=model_name,
        provider=provider,
        default_context_window=1000,
        visual_name="Gemini 3 Flash",
        reasoning={},
    )
    llm_service.llm_factory.get_llm.return_value = mock_llm

    mock_google_cls = mocker.patch("app.llms.services.InstrumentedGoogleGenAI")

    # Act
    await llm_service._get_client_instance(
        model_name=model_name,
        temperature=temperature,
        api_key=api_key,
        reasoning_config=reasoning_config,
    )

    # Assert
    mock_google_cls.assert_called_once()
    call_kwargs = mock_google_cls.call_args.kwargs

    assert call_kwargs["model"] == model_name
    assert call_kwargs["api_key"] == api_key

    gen_config = call_kwargs["generation_config"]
    assert isinstance(gen_config, types.GenerateContentConfig)
    assert gen_config.temperature == temperature

    # Verify thinking_config is present and correct
    assert gen_config.thinking_config is not None
    assert isinstance(gen_config.thinking_config, types.ThinkingConfig)
    assert gen_config.thinking_config.thinking_level == "LOW"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_name",
    [
        LLMModel.GEMINI_2_5_PRO,
        LLMModel.GEMINI_2_5_FLASH,
        LLMModel.GEMINI_2_5_FLASH_LITE,
    ],
)
async def test_get_client_instance__google_gemini_2_5__skips_thinking_config(
    llm_service, mocker, model_name
):
    """
    Scenario: Requesting a client for Gemini 2.5 models.
    Expected: thinking_config is NOT included in generation_config (API compatibility).
    """
    # Arrange
    provider = LLMProvider.GOOGLE
    temperature = 0.5
    api_key = "fake-key"
    reasoning_config = (("thinking_level", "LOW"),)  # Even if provided in settings

    mock_llm = LLM(
        model_name=model_name,
        provider=provider,
        default_context_window=1000,
        visual_name="Gemini 2.5",
        reasoning={},
    )
    llm_service.llm_factory.get_llm.return_value = mock_llm

    mock_google_cls = mocker.patch("app.llms.services.InstrumentedGoogleGenAI")

    # Act
    await llm_service._get_client_instance(
        model_name=model_name,
        temperature=temperature,
        api_key=api_key,
        reasoning_config=reasoning_config,
    )

    # Assert
    mock_google_cls.assert_called_once()
    call_kwargs = mock_google_cls.call_args.kwargs

    gen_config = call_kwargs["generation_config"]
    assert isinstance(gen_config, types.GenerateContentConfig)
    assert gen_config.temperature == temperature

    # Verify thinking_config is ABSENT
    assert gen_config.thinking_config is None


@pytest.mark.asyncio
async def test_get_client_instance__anthropic__passes_thinking_dict(
    llm_service, mocker
):
    """
    Scenario: Requesting a client for Anthropic.
    Expected: thinking_dict is passed directly to the constructor.
    """
    # Arrange
    model_name = LLMModel.CLAUDE_3_5_SONNET
    provider = LLMProvider.ANTHROPIC
    temperature = 1.0
    api_key = "fake-key"
    reasoning_config = (("type", "enabled"), ("budget_tokens", 1024))

    mock_llm = LLM(
        model_name=model_name,
        provider=provider,
        default_context_window=1000,
        visual_name="Claude 3.5 Sonnet",
        reasoning={},
    )
    llm_service.llm_factory.get_llm.return_value = mock_llm

    mock_anthropic_cls = mocker.patch("app.llms.services.InstrumentedAnthropic")

    # Act
    await llm_service._get_client_instance(
        model_name=model_name,
        temperature=temperature,
        api_key=api_key,
        reasoning_config=reasoning_config,
    )

    # Assert
    mock_anthropic_cls.assert_called_once()
    call_kwargs = mock_anthropic_cls.call_args.kwargs

    assert call_kwargs["model"] == model_name
    assert call_kwargs["temperature"] == temperature
    assert call_kwargs["api_key"] == api_key
    assert call_kwargs["thinking_dict"] == {"type": "enabled", "budget_tokens": 1024}


@pytest.mark.asyncio
async def test_get_client_instance__openai__passes_reasoning_effort(
    llm_service, mocker
):
    """
    Scenario: Requesting a client for OpenAI.
    Expected: Reasoning parameters are unpacked into kwargs.
    """
    # Arrange
    model_name = LLMModel.GPT_4_1
    provider = LLMProvider.OPENAI
    temperature = 0.8
    api_key = "fake-key"
    reasoning_config = (("reasoning_effort", "high"),)

    mock_llm = LLM(
        model_name=model_name,
        provider=provider,
        default_context_window=1000,
        visual_name="GPT 4.1",
        reasoning={},
    )
    llm_service.llm_factory.get_llm.return_value = mock_llm

    mock_openai_cls = mocker.patch("app.llms.services.InstrumentedOpenAI")

    # Act
    await llm_service._get_client_instance(
        model_name=model_name,
        temperature=temperature,
        api_key=api_key,
        reasoning_config=reasoning_config,
    )

    # Assert
    mock_openai_cls.assert_called_once()
    call_kwargs = mock_openai_cls.call_args.kwargs

    assert call_kwargs["model"] == model_name
    assert call_kwargs["temperature"] == temperature
    assert call_kwargs["api_key"] == api_key
    assert call_kwargs["reasoning_effort"] == "high"
    assert call_kwargs["additional_kwargs"] == {
        "stream_options": {"include_usage": True}
    }
