import logging
from decimal import Decimal
from app.llms.enums import LLMModel, LLMRole
from app.llms.factories import build_llm_service
from app.settings.enums import CodingMode, ContextStrategy, OperationalMode
from app.settings.repositories import SettingsRepository
from app.settings.schemas import LLMSettingsCreate, SettingsCreate
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def initialize_application_settings(db: AsyncSession) -> None:
    """
    Checks if application settings exist. If not, creates default settings.
    This should be called once at application startup.
    """
    logger.info("Checking and initializing LLM settings...")
    llm_service = await build_llm_service(db)
    all_llms = await llm_service.get_all_models()
    for llm in all_llms:
        existing_llm_setting = await llm_service.llm_settings_repo.get_by_model_name(llm.model_name)
        if not existing_llm_setting:
            logger.info(f"Seeding new LLM: {llm.model_name}")
            await llm_service.llm_settings_repo.create(
                LLMSettingsCreate(
                    model_name=llm.model_name,
                    provider=llm.provider,
                    context_window=llm.default_context_window,
                    api_key=None,
                )
            )

    settings_repo = SettingsRepository(db)
    existing_settings = await settings_repo.get(pk=1)

    if existing_settings:
        logger.info("Application settings already initialized.")
        return

    logger.info("Initializing application settings...")

    # Set the default coding LLM for the main settings
    default_llm = await llm_service.llm_settings_repo.get_by_model_name(LLMModel.GPT_4_1_MINI)
    if not default_llm:
        # This should be unreachable if the factories contains GPT_4_1, but it's a safe fallback.
        raise RuntimeError("Default LLM model GPT-4.1-mini not found after seeding. Check llms.factories._MODEL_REGISTRY.")

    # Promote default to Coder
    await llm_service.llm_settings_repo.set_active_role(default_llm.id, LLMRole.CODER)
    # todo need to fix it later, call by services. coding_llm_settings_id should not be needed here
    await settings_repo.create(
        SettingsCreate(
            operational_mode=OperationalMode.CODE,
            coding_mode=CodingMode.AGENT,
            context_strategy=ContextStrategy.MANUAL,
            max_history_length=50,
            coding_llm_temperature=Decimal("0.7"),
            ast_token_limit=10000,
            grep_token_limit=4000
        )
    )
    await db.commit()
    logger.info("Application settings initialized successfully.")
