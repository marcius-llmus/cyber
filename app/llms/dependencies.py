from sqlalchemy.ext.asyncio import AsyncSession
from app.llms.factories import get_llm_factory_instance
from app.llms.services import LLMService
from app.settings.dependencies import build_settings_service


async def build_llm_service(db: AsyncSession) -> LLMService:
    settings_service = await build_settings_service(db)
    llm_factory = await get_llm_factory_instance()
    return LLMService(settings_service=settings_service, llm_factory=llm_factory)
