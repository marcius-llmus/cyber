import logging
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


async def initialize_application_settings(db: AsyncSession) -> None:
    """
    Checks if application settings exist. If not, creates default settings.
    This should be called once at application startup.
    """
    # Use local imports to avoid circular dependency issues at startup
    from app.llms.enums import LLMModel
    from app.settings.enums import CodingMode, ContextStrategy, OperationalMode
    from app.settings.repositories import LLMSettingsRepository, SettingsRepository
    from app.settings.schemas import LLMSettingsCreate, SettingsCreate
    from app.llms.factory import LLMFactory


    settings_repo = SettingsRepository(db)
    existing_settings = await settings_repo.get(pk=1)

    if existing_settings:
        logger.info("Application settings already initialized.")
        return

    logger.info("Initializing application settings...")

    # Use repository directly for seeding to avoid service-layer exceptions on not-found.
    llm_settings_repo = LLMSettingsRepository(db)
    llm_factory = LLMFactory()
    all_llms = await llm_factory.get_all_llms()
    for llm in all_llms:
        existing_llm_setting = await llm_settings_repo.get_by_model_name(llm.model_name)
        if not existing_llm_setting:
            await llm_settings_repo.create(
                LLMSettingsCreate(
                    model_name=llm.model_name,
                    provider=llm.provider,
                    context_window=llm.default_context_window,
                    api_key=None,
                )
            )

    # Set the default coding LLM for the main settings
    default_llm = await llm_settings_repo.get_by_model_name(LLMModel.GPT_4_1)
    if not default_llm:
        # This should be unreachable if the factory contains GPT_4_1, but it's a safe fallback.
        raise RuntimeError("Default LLM model GPT-4.1 not found after seeding. Check llms.factory._MODEL_REGISTRY.")

    await settings_repo.create(
        SettingsCreate(
            operational_mode=OperationalMode.CODE,
            coding_mode=CodingMode.AGENT,
            context_strategy=ContextStrategy.MANUAL,
            max_history_length=50,
            coding_llm_temperature=Decimal("0.7"),
            ast_token_limit=10000,
            coding_llm_settings_id=default_llm.id,
        )
    )
    await db.commit()
    logger.info("Application settings initialized successfully.")