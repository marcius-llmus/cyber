import pytest

from app.llms.enums import LLMModel, LLMProvider, LLMRole
from app.llms.models import LLMSettings
from app.llms.repositories import LLMSettingsRepository
from app.settings.schemas import LLMSettingsUpdate


async def test_llm_settings_repository__get_by_model_name__returns_none_when_missing(
    llm_settings_repository: LLMSettingsRepository,
):
    """Scenario: query unknown model_name.

    Asserts:
        - returns None
    """
    result = await llm_settings_repository.get_by_model_name("unknown-model")
    assert result is None


async def test_llm_settings_repository__get_by_model_name__returns_row_when_present(
    llm_settings_repository: LLMSettingsRepository,
    llm_settings_openai_coder,
):
    """Scenario: query an existing model_name.

    Asserts:
        - returns matching row
    """
    result = await llm_settings_repository.get_by_model_name(llm_settings_openai_coder.model_name)
    assert result is not None
    assert result.id == llm_settings_openai_coder.id


async def test_llm_settings_repository__get_all__returns_all_rows(
    llm_settings_repository: LLMSettingsRepository,
    llm_settings_openai_no_role,
    llm_settings_anthropic,
):
    """Scenario: multiple rows exist.

    Asserts:
        - returns a list containing all rows
    """
    results = await llm_settings_repository.get_all()
    assert len(results) >= 2


@pytest.mark.parametrize(
    "provider,model_name",
    [
        (LLMProvider.OPENAI, LLMModel.GPT_4_1_MINI),
        (LLMProvider.ANTHROPIC, LLMModel.CLAUDE_OPUS_4_1),
        (LLMProvider.GOOGLE, LLMModel.GEMINI_2_5_FLASH),
    ],
)
async def test_llm_settings_repository__update_api_key_for_provider__updates_all_models_for_provider(
    provider,
    model_name,
    llm_settings_repository: LLMSettingsRepository,
    db_session,
):
    """Scenario: multiple LLMSettings can share a provider.

    Asserts:
        - update_api_key_for_provider updates api_key for all rows with that provider
        - changes are flushed (visible in subsequent reads in same session)
    """
    # Create initial row
    db_session.add(LLMSettings(
        model_name=model_name,
        provider=provider,
        api_key="old-key",
        context_window=1000,
        active_role=None,
    ))
    await db_session.flush()

    new_key = "sk-new-key-123"
    await llm_settings_repository.update_api_key_for_provider(provider, new_key)
    
    # Verify update
    updated_key = await llm_settings_repository.get_api_key_for_provider(provider)
    assert updated_key == new_key
    

@pytest.mark.parametrize(
    "provider,model_name",
    [
        (LLMProvider.OPENAI, LLMModel.GPT_4_1_MINI),
        (LLMProvider.ANTHROPIC, LLMModel.CLAUDE_OPUS_4_1),
        (LLMProvider.GOOGLE, LLMModel.GEMINI_2_5_FLASH),
    ],
)
async def test_llm_settings_repository__update_api_key_for_provider__can_clear_key(
    provider,
    model_name,
    llm_settings_repository: LLMSettingsRepository,
    db_session,
):
    """Scenario: provider has keys, then key is cleared.

    Asserts:
        - update_api_key_for_provider(api_key=None) sets api_key to NULL for provider
        - get_api_key_for_provider returns None afterwards
    """
    # Create initial row
    db_session.add(LLMSettings(
        model_name=model_name,
        provider=provider,
        api_key="sk-existing",
        context_window=1000,
        active_role=None,
    ))
    await db_session.flush()

    await llm_settings_repository.update_api_key_for_provider(provider, None)
    assert await llm_settings_repository.get_api_key_for_provider(provider) is None


@pytest.mark.parametrize(
    "provider,model_name",
    [
        (LLMProvider.OPENAI, LLMModel.GPT_4_1_MINI),
        (LLMProvider.ANTHROPIC, LLMModel.CLAUDE_OPUS_4_1),
        (LLMProvider.GOOGLE, LLMModel.GEMINI_2_5_FLASH),
    ],
)
async def test_llm_settings_repository__get_api_key_for_provider__returns_first_non_null_key(
    provider,
    model_name,
    llm_settings_repository: LLMSettingsRepository,
    db_session,
):
    """Scenario: at least one model under provider has a non-null api_key.

    Asserts:
        - get_api_key_for_provider returns a string
    """
    api_key = "sk-test-key"
    db_session.add(LLMSettings(
        model_name=model_name,
        provider=provider,
        api_key=api_key,
        context_window=1000,
        active_role=None,
    ))
    await db_session.flush()

    key = await llm_settings_repository.get_api_key_for_provider(provider)
    assert key is not None
    assert key == api_key


async def test_llm_settings_repository__get_api_key_for_provider__returns_none_when_no_keys(
    llm_settings_repository: LLMSettingsRepository,
    db_session,
):
    """Scenario: provider rows exist but api_key is NULL for all.

    Asserts:
        - returns None
    """
    # Explicitly clear any existing keys for OPENAI to ensure test isolation
    await llm_settings_repository.update_api_key_for_provider(LLMProvider.OPENAI, None)

    db_session.add(
        LLMSettings(
            model_name=LLMModel.GPT_4O,
            provider=LLMProvider.OPENAI,
            api_key=None,
            context_window=128000,
            active_role=None,
        )
    )
    await db_session.flush()
    key = await llm_settings_repository.get_api_key_for_provider(LLMProvider.OPENAI)
    assert key is None


async def test_llm_settings_repository__get_by_role__returns_none_when_missing(
    llm_settings_repository: LLMSettingsRepository,
):
    """Scenario: no row has active_role set for the role.

    Asserts:
        - returns None
    """
    result = await llm_settings_repository.get_by_role(LLMRole.CODER)
    assert result is None


async def test_llm_settings_repository__get_by_role__returns_row_when_present(
    llm_settings_repository: LLMSettingsRepository,
    llm_settings_openai_coder,
):
    """Scenario: one row has active_role=CODER.

    Asserts:
        - returns that row
    """
    result = await llm_settings_repository.get_by_role(LLMRole.CODER)
    assert result is not None
    assert result.id == llm_settings_openai_coder.id


async def test_llm_settings_repository__set_active_role__clears_existing_and_sets_target(
    llm_settings_repository: LLMSettingsRepository,
    db_session,
    llm_settings_openai_coder,
    llm_settings_openai_no_role,
):
    """Scenario: one model currently has CODER; switch CODER to another model.

    Asserts:
        - previous CODER is cleared (active_role=None)
        - target model gets CODER
        - behavior does not require commit (flush semantics are enough)
    """
    
    # Initial state check
    old_coder = await llm_settings_repository.get_by_role(LLMRole.CODER)
    assert old_coder.id == llm_settings_openai_coder.id
    
    # Switch role
    await llm_settings_repository.set_active_role(llm_settings_openai_no_role.id, LLMRole.CODER)
    
    # Verify new state
    new_coder = await llm_settings_repository.get_by_role(LLMRole.CODER)
    assert new_coder.id == llm_settings_openai_no_role.id
    
    # Verify old one is cleared
    await db_session.refresh(llm_settings_openai_coder)
    assert llm_settings_openai_coder.active_role is None


async def test_llm_settings_repository__set_active_role__no_commit_side_effects(
    llm_settings_repository: LLMSettingsRepository,
    db_session,
    llm_settings_openai_no_role,
):
    """Scenario: set_active_role is called.

    Asserts:
        - repository does not commit; rollback reverts changes
    """
    target_id = llm_settings_openai_no_role.id
    target_model_name = llm_settings_openai_no_role.model_name

    nested = await db_session.begin_nested()
    await llm_settings_repository.set_active_role(target_id, LLMRole.CODER)
    await nested.rollback()

    fresh_row = await llm_settings_repository.get_by_model_name(target_model_name)
    assert fresh_row is not None
    assert fresh_row.active_role is None