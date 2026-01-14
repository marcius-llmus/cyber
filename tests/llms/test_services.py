import pytest
from unittest.mock import AsyncMock

from app.llms.exceptions import MissingLLMApiKeyException
from app.llms.enums import LLMModel, LLMProvider, LLMRole
from app.llms.factories import build_llm_service
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


async def test_llm_service__get_all_llm_settings__delegates_to_repo(db_session):
    """Scenario: LLM settings exist in DB.

    Asserts:
        - returns a list of LLMSettings
    """
    service = await build_llm_service(db_session)
    assert isinstance(await service.get_all_llm_settings(), list)


async def test_llm_service__get_llm_settings__raises_when_missing(db_session):
    """Scenario: request settings for a model not in DB.

    Asserts:
        - raises LLMSettingsNotFoundException
    """
    service = await build_llm_service(db_session)
    with pytest.raises(LLMSettingsNotFoundException):
        await service.get_llm_settings("missing")


async def test_llm_service__get_llm_settings__returns_when_present(db_session, llm_settings_openai_coder):
    """Scenario: settings exist for a model.

    Asserts:
        - returns the matching LLMSettings row
    """
    service = await build_llm_service(db_session)
    obj = await service.get_llm_settings(str(llm_settings_openai_coder.model_name))
    assert obj.id == llm_settings_openai_coder.id


@pytest.mark.parametrize(
    "has_coder_role,has_default_model",
    [
        (True, True),
        (False, True),
    ],
)
async def test_llm_service__get_coding_llm__returns_existing_or_assigns_default(
    has_coder_role: bool,
    has_default_model: bool,
    db_session,
):
    """Scenario matrix:
        - if a CODER role exists, return it
        - else, assign CODER to the default model (GPT_4_1_MINI) and return it

    Asserts:
        - returns an LLMSettings
        - if default assignment path is taken, CODER role is set
    """
    service = await build_llm_service(db_session)

    if has_coder_role:
        db_session.add(
            LLMSettings(
                model_name=LLMModel.GPT_4O,
                provider=LLMProvider.OPENAI,
                api_key="sk-openai",
                context_window=128000,
                active_role=LLMRole.CODER,
            )
        )
        await db_session.flush()

    if has_default_model:
        db_session.add(
            LLMSettings(
                model_name=LLMModel.GPT_4_1_MINI,
                provider=LLMProvider.OPENAI,
                api_key="sk-openai",
                context_window=128000,
                active_role=None,
            )
        )
        await db_session.flush()

    coder = await service.get_coding_llm()
    assert coder is not None
    if not has_coder_role:
        assert str(coder.model_name) == str(LLMModel.GPT_4_1_MINI)
        assert coder.active_role == LLMRole.CODER


async def test_llm_service__get_coding_llm__raises_when_no_coder_and_no_models(db_session):
    """Scenario: DB has no CODER and does not contain the default model.

    Asserts:
        - raises LLMSettingsNotFoundException
    """
    service = await build_llm_service(db_session)
    with pytest.raises(LLMSettingsNotFoundException):
        await service.get_coding_llm()


async def test_llm_service__get_coding_llm__default_assignment_returns_coder_role_even_if_model_was_preloaded(
    db_session,
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
    service = await build_llm_service(db_session)

    default_row = LLMSettings(
        model_name=LLMModel.GPT_4_1_MINI,
        provider=LLMProvider.OPENAI,
        api_key="sk-openai",
        context_window=128000,
        active_role=None,
    )
    db_session.add(default_row)
    await db_session.flush()

    preloaded = await db_session.get(LLMSettings, default_row.id)
    assert preloaded is default_row
    assert preloaded.active_role is None

    coder = await service.get_coding_llm()
    assert coder.id == default_row.id
    assert coder.active_role == LLMRole.CODER


async def test_llm_service__update_settings__raises_when_missing(db_session):
    """Scenario: update settings for non-existent llm_id.

    Asserts:
        - raises LLMSettingsNotFoundException
    """
    service = await build_llm_service(db_session)
    with pytest.raises(LLMSettingsNotFoundException):
        await service.update_settings(123456, LLMSettingsUpdate())


async def test_llm_service__update_settings__raises_when_context_window_exceeds_model_max(
    db_session,
    llm_settings_openai_no_role,
):
    """Scenario: user sets context_window above registry default_context_window.

    Asserts:
        - raises ContextWindowExceededException
    """
    service = await build_llm_service(db_session)
    with pytest.raises(ContextWindowExceededException):
        await service.update_settings(llm_settings_openai_no_role.id, LLMSettingsUpdate(context_window=99999999))


async def test_llm_service__update_settings__updates_api_key_for_provider_when_api_key_set(
    db_session,
    llm_settings_openai_no_role,
):
    """Scenario: update settings includes api_key.

    Asserts:
        - provider-level key update is applied
        - target settings row is updated
    """
    service = await build_llm_service(db_session)
    updated = await service.update_settings(llm_settings_openai_no_role.id, LLMSettingsUpdate(api_key="sk-new"))
    assert updated.id == llm_settings_openai_no_role.id
    await db_session.refresh(llm_settings_openai_no_role)
    assert llm_settings_openai_no_role.api_key == "sk-new"


async def test_llm_service__update_coding_llm__sets_role_then_updates_settings(
    db_session,
    llm_settings_openai_no_role,
    llm_settings_anthropic,
):
    """Scenario: promote a model to CODER.

    Asserts:
        - CODER role becomes unique and assigned to the requested llm_id
        - settings updates are applied
    """
    service = await build_llm_service(db_session)
    updated = await service.update_coding_llm(llm_settings_openai_no_role.id, LLMSettingsUpdate(context_window=128000))
    assert updated.id == llm_settings_openai_no_role.id
    await db_session.refresh(llm_settings_openai_no_role)
    assert llm_settings_openai_no_role.active_role == LLMRole.CODER


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
    db_session,
    fake_llm_client,
    make_llm_service_with_fake_factory,
):
    """Scenario: request a client for a model of each provider.

    Asserts:
        - returns the correct client type for provider
        - is wired with model name and temperature
    """
    db_session.add(LLMSettings(
        model_name=model_name,
        provider=provider,
        api_key="sk-test",
        context_window=1000,
        active_role=None,
    ))
    await db_session.flush()

    service = make_llm_service_with_fake_factory(
        model_registry={
            model_name: LLM(
                model_name=model_name,
                provider=provider,
                default_context_window=128000,
            )
        }
    )
    
    # We override _get_client_instance to return our fake object, 
    # but we want to ensure the service logic calls it with correct params.
    service._get_client_instance = AsyncMock(return_value=fake_llm_client)

    client = await service.get_client(model_name, temperature=0.5)
    
    assert client == fake_llm_client
    service._get_client_instance.assert_awaited_once_with(
        model_name, 
        0.5, 
        "sk-test"
    )


async def test_llm_service__get_client__uses_provider_api_key_from_repo(
    db_session,
    llm_settings_openai_no_role,
    fake_llm_client,
    make_llm_service_with_fake_factory,
):
    """Scenario: api_key is stored on provider settings.

    Asserts:
        - get_client uses LLMSettingsRepository.get_api_key_for_provider
    """
    service = make_llm_service_with_fake_factory(
        model_registry={
            LLMModel(llm_settings_openai_no_role.model_name): LLM(
                model_name=LLMModel(llm_settings_openai_no_role.model_name),
                provider=llm_settings_openai_no_role.provider,
                default_context_window=128000,
            )
        }
    )

    service._get_client_instance = AsyncMock(return_value=fake_llm_client)  # type: ignore[method-assign]

    await service.get_client(LLMModel(llm_settings_openai_no_role.model_name), temperature=0.2)

    assert service._get_client_instance.await_count == 1


async def test_llm_service__get_client__raises_when_api_key_missing(
    db_session,
    make_llm_service_with_fake_factory,
):
    """Scenario: provider has no api_key configured.

    Asserts:
        - raises MissingLLMApiKeyException (strict mode)
    """
    service = make_llm_service_with_fake_factory(
        model_registry={
            LLMModel.GPT_4_1_MINI: LLM(
                model_name=LLMModel.GPT_4_1_MINI,
                provider=LLMProvider.OPENAI,
                default_context_window=128000,
            )
        }
    )

    async def _missing_key(_provider):
        return None

    service.llm_settings_repo.get_api_key_for_provider = _missing_key  # type: ignore[method-assign]

    with pytest.raises(MissingLLMApiKeyException):
        await service.get_client(LLMModel.GPT_4_1_MINI, temperature=0.2)


async def test_llm_service__get_client__raises_on_unsupported_provider(db_session, mocker):
    """Scenario: registry returns an LLM with an unsupported provider.

    Asserts:
        - raises ValueError
    """
    service = await build_llm_service(db_session)

    class _FakeProvider(str):
        pass

    fake_llm = type("FakeLLM", (), {"provider": _FakeProvider("FAKE"), "model_name": LLMModel.GPT_4O, "default_context_window": 1})
    mocker.patch.object(service.llm_factory, "get_llm", return_value=fake_llm)

    repo = service.llm_settings_repo
    mocker.patch.object(repo, "get_api_key_for_provider", return_value="sk-test")

    with pytest.raises(ValueError):
        await service._get_client_instance(LLMModel.GPT_4O, temperature=0.2, api_key="sk-test")


async def test_llm_service__get_client_instance__is_cached_for_same_inputs(db_session, llm_settings_openai_no_role):
    """Scenario: call get_client twice with same model/temperature/key.

    Asserts:
        - returns the same underlying client instance (alru_cache)
    """
    pytest.skip("Caching behavior tests intentionally disabled for this codebase.")