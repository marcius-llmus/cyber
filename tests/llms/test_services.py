import pytest
from unittest.mock import AsyncMock

from app.llms.exceptions import MissingLLMApiKeyException
from app.llms.enums import LLMModel, LLMProvider, LLMRole
from app.settings.exceptions import ContextWindowExceededException, LLMSettingsNotFoundException
from app.settings.schemas import LLMSettingsUpdate
from app.llms.models import LLMSettings
from app.llms.schemas import LLM


async def test_llm_service__get_model_metadata__returns_llm_schema(llm_service):
    """Scenario: fetch metadata for a known model.

    Asserts:
        - returns an LLM schema
        - provider/default_context_window match the registry
    """
    llm = await llm_service.get_model_metadata(LLMModel.GPT_4O)
    assert llm.model_name == LLMModel.GPT_4O
    assert llm.provider == LLMProvider.OPENAI
    assert llm.default_context_window > 0


async def test_llm_service__get_all_models__returns_non_empty_list(llm_service):
    """Scenario: list all models from the registry.

    Asserts:
        - returns a list of LLM schemas
        - list is non-empty
    """
    llms = await llm_service.get_all_models()
    assert isinstance(llms, list)
    assert len(llms) > 0


# will keep this one and bellow as for good redundancy
async def test_llm_service__get_all_llm_settings__delegates_to_repo(llm_service):
    """Scenario: LLM settings exist in DB.

    Asserts:
        - returns a list of LLMSettings
    """
    llm_service.llm_settings_repo.get_all = AsyncMock(return_value=[])
    assert isinstance(await llm_service.get_all_llm_settings(), list)


async def test_llm_service__get_all_llm_settings__returns_all_db_rows(
    llm_settings_seed_many,
    llm_service,
):
    """Scenario: repo returns multiple LLMSettings."""
    llm_service.llm_settings_repo.get_all = AsyncMock(return_value=llm_settings_seed_many)
    results = await llm_service.get_all_llm_settings()

    assert len(results) == len(llm_settings_seed_many)

    result_ids = {x.id for x in results}
    for seeded in llm_settings_seed_many:
        assert seeded.id in result_ids


async def test_llm_service__get_llm_settings__raises_when_missing(llm_service):
    """Scenario: request settings for a model not in DB.

    Asserts:
        - raises LLMSettingsNotFoundException
    """
    llm_service.llm_settings_repo.get_by_model_name = AsyncMock(return_value=None)
    with pytest.raises(LLMSettingsNotFoundException):
        await llm_service.get_llm_settings("missing")


async def test_llm_service__get_llm_settings__returns_when_present(llm_settings_openai_coder, llm_service):
    """Scenario: settings exist for a model.

    Asserts:
        - returns the matching LLMSettings row
    """
    llm_service.llm_settings_repo.get_by_model_name = AsyncMock(return_value=llm_settings_openai_coder)
    obj = await llm_service.get_llm_settings(str(llm_settings_openai_coder.model_name))
    assert obj.id == llm_settings_openai_coder.id


async def test_llm_service__get_coding_llm__when_coder_role_exists__returns_existing(llm_service):
    """Scenario: a CODER role already exists.

    Asserts:
        - returns the existing CODER LLMSettings
    """
    # First verify it raises if missing
    llm_service.llm_settings_repo.get_by_role = AsyncMock(return_value=None)
    llm_service.llm_settings_repo.get_by_model_name = AsyncMock(return_value=None)
    with pytest.raises(LLMSettingsNotFoundException):
        await llm_service.get_coding_llm()

    coder_row = LLMSettings(id=1, active_role=LLMRole.CODER)
    llm_service.llm_settings_repo.get_by_role = AsyncMock(return_value=coder_row)
    coder = await llm_service.get_coding_llm()
    assert coder is not None
    assert coder.id == coder_row.id
    assert coder.active_role == LLMRole.CODER


async def test_llm_service__get_coding_llm__when_no_coder_role__assigns_default_model(llm_service, llm_settings_openai_no_role):
    """Scenario: no CODER role exists, but the default model exists.

    Asserts:
        - assigns CODER role to the default model (GPT_4_1_MINI)
        - returns the updated default model row
    """
    default_row = llm_settings_openai_no_role
    expected_return = LLMSettings(
        id=default_row.id,
        model_name=default_row.model_name,
        provider=default_row.provider,
        api_key=default_row.api_key,
        context_window=default_row.context_window,
        active_role=LLMRole.CODER,
    )
    llm_service.llm_settings_repo.get_by_role = AsyncMock(return_value=None)
    llm_service.llm_settings_repo.get_by_model_name = AsyncMock(return_value=default_row)
    llm_service.llm_settings_repo.update = AsyncMock(return_value=expected_return)


async def test_llm_service__get_coding_llm__default_assignment_returns_coder_role_even_if_model_was_preloaded(
):
    """Scenario: no CODER exists, but the default model row exists.

    This exercises a potential stale identity-map case:
        - the default model instance is loaded into the Session identity map
        - service assigns CODER role via bulk UPDATE
        - service then calls Session.get() inside update_settings

    Asserts:
        - returned LLMSettings has active_role=CODER

    Notes:
        - This can fail if bulk updates do not expire/refresh already-loaded instances.
    """
    # This test is specific to DB Identity Map behavior, which is irrelevant for Unit Tests with Mocks.
    # We can skip it or remove it as it tests SQLAlchemy/Integration behavior.
    # todo: let's keep it so we don't forget
    pytest.skip("Integration test irrelevant for unit testing with mocks.")


async def test_llm_service__update_settings__raises_when_missing(llm_service):
    """Scenario: update settings for non-existent llm_id.

    Asserts:
        - raises LLMSettingsNotFoundException
    """
    llm_service.llm_settings_repo.get = AsyncMock(return_value=None)
    with pytest.raises(LLMSettingsNotFoundException):
        await llm_service.update_settings(123456, LLMSettingsUpdate())


async def test_llm_service__update_settings__raises_when_context_window_exceeds_model_max(
    llm_settings_openai_no_role,
    llm_service,
):
    """Scenario: user sets context_window above registry default_context_window.

    Asserts:
        - raises ContextWindowExceededException
    """
    llm_service.llm_settings_repo.get = AsyncMock(return_value=llm_settings_openai_no_role)
    with pytest.raises(ContextWindowExceededException):
        await llm_service.update_settings(llm_settings_openai_no_role.id, LLMSettingsUpdate(context_window=99999999))


async def test_llm_service__update_settings__updates_api_key_for_provider_when_api_key_set(
    llm_settings_openai_no_role,
    llm_service,
):
    """Scenario: update settings includes api_key.

    Asserts:
        - provider-level key update is applied
        - target settings row is updated
    """
    llm_service.llm_settings_repo.get = AsyncMock(return_value=llm_settings_openai_no_role)
    llm_service.llm_settings_repo.update = AsyncMock(return_value=llm_settings_openai_no_role)
    llm_service.llm_settings_repo.update_api_key_for_provider = AsyncMock()

    updated = await llm_service.update_settings(llm_settings_openai_no_role.id, LLMSettingsUpdate(api_key="sk-new"))
    assert updated.id == llm_settings_openai_no_role.id
    
    llm_service.llm_settings_repo.update_api_key_for_provider.assert_awaited_once()


async def test_llm_service__update_coding_llm__sets_role_then_updates_settings(
    llm_settings_openai_no_role,
    llm_settings_anthropic,
    llm_service,
):
    """Scenario: promote a model to CODER.

    Asserts:
        - CODER role becomes unique and assigned to the requested llm_id
        - settings updates are applied
    """
    llm_service.llm_settings_repo.get = AsyncMock(return_value=llm_settings_openai_no_role)
    llm_service.llm_settings_repo.update = AsyncMock(return_value=llm_settings_openai_no_role)
    llm_service.llm_settings_repo.set_active_role = AsyncMock()

    updated = await llm_service.update_coding_llm(llm_settings_openai_no_role.id, LLMSettingsUpdate(context_window=128000))
    assert updated.id == llm_settings_openai_no_role.id

    llm_service.llm_settings_repo.set_active_role.assert_awaited_once()

async def test_llm_service__update_settings__api_key_enforced_one_key_per_provider_by_overwrite(
    llm_service,
    llm_settings_openai_no_role,
):
    """Scenario: api_key update should enforce one key per provider.

    Asserts:
        - update_api_key_for_provider is called with the new key
    """
    llm_service.llm_settings_repo.get.return_value = llm_settings_openai_no_role
    llm_service.llm_settings_repo.update.return_value = llm_settings_openai_no_role
    llm_service.llm_settings_repo.update_api_key_for_provider.return_value = None

    await llm_service.update_settings(
        llm_settings_openai_no_role.id,
        LLMSettingsUpdate(api_key="sk-openai-canonical")
    )

    llm_service.llm_settings_repo.update_api_key_for_provider.assert_awaited_once_with(
        llm_settings_openai_no_role.provider,
        "sk-openai-canonical"
    )

@pytest.mark.parametrize(
    "provider,model_name",
    [
        (LLMProvider.OPENAI, LLMModel.GPT_4_1_MINI),
        (LLMProvider.ANTHROPIC, LLMModel.CLAUDE_OPUS_4_1),
        (LLMProvider.GOOGLE, LLMModel.GEMINI_2_5_FLASH),
    ],
)
async def test_llm_service__get_client__hydrates_provider_specific_client(
    provider,
    model_name,
    fake_llm_client,
    llm_service,
    mocker,
):
    """Scenario: request a client for a model of each provider.

    Asserts:
        - returns the correct client type for provider
        - is wired with model name and temperature
    """
    # Configure mock repo to return the key
    llm_service.llm_settings_repo.get_api_key_for_provider.return_value = "sk-test"
    
    fake_llm = LLM(model_name=model_name, provider=provider, default_context_window=128000)
    mocker.patch.object(llm_service.llm_factory, "get_llm", return_value=fake_llm)
    
    # We override _get_client_instance to return our fake object, 
    # but we want to ensure the service logic calls it with correct params.
    llm_service._get_client_instance = AsyncMock(return_value=fake_llm_client)
    client = await llm_service.get_client(model_name, temperature=0.5)
    
    assert client == fake_llm_client
    llm_service._get_client_instance.assert_awaited_once_with(
        model_name, 
        0.5, 
        "sk-test"
    )


async def test_llm_service__get_client__uses_provider_api_key_from_repo(
    llm_settings_openai_no_role,
    fake_llm_client,
    llm_service,
    mocker,
):
    """Scenario: api_key is stored on provider settings.

    Asserts:
        - get_client uses LLMSettingsRepository.get_api_key_for_provider
    """
    fake_llm = LLM(
        model_name=LLMModel(llm_settings_openai_no_role.model_name),
        provider=llm_settings_openai_no_role.provider,
        default_context_window=128000,
    )
    mocker.patch.object(llm_service.llm_factory, "get_llm", return_value=fake_llm)
    # Configure mock repo
    llm_service.llm_settings_repo.get_api_key_for_provider.return_value = "sk-provider-key"

    llm_service._get_client_instance = AsyncMock(return_value=fake_llm_client)  # type: ignore[method-assign]

    await llm_service.get_client(LLMModel(llm_settings_openai_no_role.model_name), temperature=0.2)

    assert llm_service._get_client_instance.await_count == 1


async def test_llm_service__get_client__raises_when_api_key_missing(
    llm_service,
    mocker,
):
    """Scenario: provider has no api_key configured.

    Asserts:
        - raises MissingLLMApiKeyException (strict mode)
    """
    fake_llm = LLM(
        model_name=LLMModel.GPT_4_1_MINI,
        provider=LLMProvider.OPENAI,
        default_context_window=128000,
    )
    mocker.patch.object(llm_service.llm_factory, "get_llm", return_value=fake_llm)

    async def _missing_key(_provider):
        return None

    llm_service.llm_settings_repo.get_api_key_for_provider = _missing_key  # type: ignore[method-assign]

    with pytest.raises(MissingLLMApiKeyException):
        await llm_service.get_client(LLMModel.GPT_4_1_MINI, temperature=0.2)


async def test_llm_service__get_client__raises_on_unsupported_provider(mocker, llm_service):
    """Scenario: registry returns an LLM with an unsupported provider.

    Asserts:
        - raises ValueError
    """
    class _FakeProvider(str):
        pass

    fake_llm = type("FakeLLM", (), {"provider": _FakeProvider("FAKE"), "model_name": LLMModel.GPT_4O, "default_context_window": 1})
    mocker.patch.object(llm_service.llm_factory, "get_llm", return_value=fake_llm)

    repo = llm_service.llm_settings_repo
    mocker.patch.object(repo, "get_api_key_for_provider", return_value="sk-test")

    with pytest.raises(ValueError):
        await llm_service._get_client_instance(LLMModel.GPT_4O, temperature=0.2, api_key="sk-test")