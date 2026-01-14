import pytest

from app.llms.services import LLMService

from app.llms.enums import LLMModel, LLMProvider, LLMRole
from app.llms.models import LLMSettings
from app.llms.repositories import LLMSettingsRepository
from app.settings.schemas import LLMSettingsUpdate


async def test_llm_settings_repository__get_by_model_name__returns_none_when_missing(db_session):
    """Scenario: query unknown model_name.

    Asserts:
        - returns None
    """
    repo = LLMSettingsRepository(db_session)
    result = await repo.get_by_model_name("unknown-model")
    assert result is None


async def test_llm_settings_repository__get_by_model_name__returns_row_when_present(
    db_session,
    llm_settings_openai_coder,
):
    """Scenario: query an existing model_name.

    Asserts:
        - returns matching row
    """
    repo = LLMSettingsRepository(db_session)
    result = await repo.get_by_model_name(llm_settings_openai_coder.model_name)
    assert result is not None
    assert result.id == llm_settings_openai_coder.id


async def test_llm_settings_repository__get_all__returns_all_rows(
    db_session,
    llm_settings_openai_no_role,
    llm_settings_anthropic,
):
    """Scenario: multiple rows exist.

    Asserts:
        - returns a list containing all rows
    """
    repo = LLMSettingsRepository(db_session)
    results = await repo.get_all()
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

    repo = LLMSettingsRepository(db_session)
    
    new_key = "sk-new-key-123"
    await repo.update_api_key_for_provider(provider, new_key)
    
    # Verify update
    updated_key = await repo.get_api_key_for_provider(provider)
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

    repo = LLMSettingsRepository(db_session)

    await repo.update_api_key_for_provider(provider, None)
    assert await repo.get_api_key_for_provider(provider) is None


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

    repo = LLMSettingsRepository(db_session)
    
    key = await repo.get_api_key_for_provider(provider)
    assert key is not None
    assert key == api_key


async def test_llm_settings_repository__get_api_key_for_provider__returns_none_when_no_keys(db_session):
    """Scenario: provider rows exist but api_key is NULL for all.

    Asserts:
        - returns None
    """
    repo = LLMSettingsRepository(db_session)
    # Explicitly clear any existing keys for OPENAI to ensure test isolation
    await repo.update_api_key_for_provider(LLMProvider.OPENAI, None)

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
    key = await repo.get_api_key_for_provider(LLMProvider.OPENAI)
    assert key is None


async def test_llm_settings_repository__get_by_role__returns_none_when_missing(db_session):
    """Scenario: no row has active_role set for the role.

    Asserts:
        - returns None
    """
    repo = LLMSettingsRepository(db_session)
    result = await repo.get_by_role(LLMRole.CODER)
    assert result is None


async def test_llm_settings_repository__get_by_role__returns_row_when_present(
    db_session,
    llm_settings_openai_coder,
):
    """Scenario: one row has active_role=CODER.

    Asserts:
        - returns that row
    """
    repo = LLMSettingsRepository(db_session)
    result = await repo.get_by_role(LLMRole.CODER)
    assert result is not None
    assert result.id == llm_settings_openai_coder.id


async def test_llm_settings_repository__set_active_role__clears_existing_and_sets_target(
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
    repo = LLMSettingsRepository(db_session)
    
    # Initial state check
    old_coder = await repo.get_by_role(LLMRole.CODER)
    assert old_coder.id == llm_settings_openai_coder.id
    
    # Switch role
    await repo.set_active_role(llm_settings_openai_no_role.id, LLMRole.CODER)
    
    # Verify new state
    new_coder = await repo.get_by_role(LLMRole.CODER)
    assert new_coder.id == llm_settings_openai_no_role.id
    
    # Verify old one is cleared
    await db_session.refresh(llm_settings_openai_coder)
    assert llm_settings_openai_coder.active_role is None


async def test_llm_settings_repository__set_active_role__no_commit_side_effects(db_session, llm_settings_openai_no_role):
    """Scenario: set_active_role is called.

    Asserts:
        - repository does not commit; rollback reverts changes
    """
    repo = LLMSettingsRepository(db_session)
    target_id = llm_settings_openai_no_role.id
    target_model_name = llm_settings_openai_no_role.model_name

    nested = await db_session.begin_nested()
    await repo.set_active_role(target_id, LLMRole.CODER)
    await nested.rollback()

    fresh_row = await repo.get_by_model_name(target_model_name)
    assert fresh_row is not None
    assert fresh_row.active_role is None