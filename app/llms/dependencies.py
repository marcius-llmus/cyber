from functools import cache

from app.llms.factory import LLMFactory


@cache
def get_llm_factory() -> LLMFactory:
    return LLMFactory()