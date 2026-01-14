import pytest
from app.llms.repositories import LLMSettingsRepository
from app.llms.enums import LLMRole, LLMProvider


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
    "provider_fixture_name",
    [
        "llm_settings_openai_no_role",
        "llm_settings_anthropic",
        "llm_settings_google",
    ],
)
async def test_llm_settings_repository__update_api_key_for_provider__updates_all_models_for_provider(
    provider_fixture_name: str,
    request,
    db_session,
):
    """Scenario: multiple LLMSettings can share a provider.

    Asserts:
        - update_api_key_for_provider updates api_key for all rows with that provider
        - changes are flushed (visible in subsequent reads in same session)
    """
    existing_row = request.getfixturevalue(provider_fixture_name)
    provider = existing_row.provider
    repo = LLMSettingsRepository(db_session)
    
    new_key = "sk-new-key-123"
    await repo.update_api_key_for_provider(provider, new_key)
    
    # Verify update
    updated_key = await repo.get_api_key_for_provider(provider)
    assert updated_key == new_key
    

@pytest.mark.parametrize(
    "provider_fixture_name",
    [
        "llm_settings_openai_no_role",
        "llm_settings_anthropic",
        "llm_settings_google",
    ],
)
async def test_llm_settings_repository__update_api_key_for_provider__can_clear_key(
    provider_fixture_name: str,
    request,
    db_session,
):
    """Scenario: provider has keys, then key is cleared.

    Asserts:
        - update_api_key_for_provider(api_key=None) sets api_key to NULL for provider
        - get_api_key_for_provider returns None afterwards
    """
    existing_row = request.getfixturevalue(provider_fixture_name)
    provider = existing_row.provider
    repo = LLMSettingsRepository(db_session)

    await repo.update_api_key_for_provider(provider, None)
    assert await repo.get_api_key_for_provider(provider) is None


@pytest.mark.parametrize(
    "provider_fixture_name",
    [
        "llm_settings_openai_no_role",
        "llm_settings_anthropic",
        "llm_settings_google",
    ],
)
async def test_llm_settings_repository__get_api_key_for_provider__returns_first_non_null_key(
    provider_fixture_name: str,
    request,
    db_session,
):
    """Scenario: at least one model under provider has a non-null api_key.

    Asserts:
        - get_api_key_for_provider returns a string
    """
    existing_row = request.getfixturevalue(provider_fixture_name)
    provider = existing_row.provider
    repo = LLMSettingsRepository(db_session)
    
    key = await repo.get_api_key_for_provider(provider)
    assert key is not None
    assert key == existing_row.api_key


async def test_llm_settings_repository__get_api_key_for_provider__returns_none_when_no_keys(db_session):
    """Scenario: provider rows exist but api_key is NULL for all.

    Asserts:
        - returns None
    """
    repo = LLMSettingsRepository(db_session)
    key = await repo.get_api_key_for_provider(LLMProvider.OPENAI)
    assert key is None


async def test_llm_settings_repository__get_api_key_for_provider__when_multiple_keys__returns_any(
    db_session,
    llm_settings_openai_no_role,
):
    """Scenario: multiple rows share a provider and more than one has a non-null api_key.

    Notes:
        - repository currently does not define ordering; this test only asserts returned key is one of them.

    Asserts:
        - returns a non-null key that belongs to a row of that provider
    """
    from app.llms.models import LLMSettings
    from app.llms.enums import LLMModel

    llm_settings_openai_no_role.api_key = "sk-openai-1"
    db_session.add(
        LLMSettings(
            model_name=LLMModel.GPT_4O,
            provider=LLMProvider.OPENAI,
            api_key="sk-openai-2",
            context_window=128000,
            active_role=None,
        )
    )
    await db_session.flush()

    repo = LLMSettingsRepository(db_session)
    key = await repo.get_api_key_for_provider(LLMProvider.OPENAI)
    assert key in {"sk-openai-1", "sk-openai-2"}


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
    
    # NOTE: repository does not flush; ensure state is visible for subsequent reads
    await db_session.flush()
    
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
    await repo.set_active_role(llm_settings_openai_no_role.id, LLMRole.CODER)
    
    await db_session.rollback()
    
    await db_session.refresh(llm_settings_openai_no_role)
    assert llm_settings_openai_no_role.active_role is None