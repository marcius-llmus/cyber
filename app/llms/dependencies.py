from async_lru import alru_cache
from app.llms.factory import LLMFactory


@alru_cache
async def get_llm_factory_instance() -> LLMFactory:
    """This function creates and caches a single instance of LLMFactory."""
    return LLMFactory()


async def get_llm_factory() -> LLMFactory:
    """FastAPI dependency provider that returns the singleton LLMFactory instance."""
    return await get_llm_factory_instance()
