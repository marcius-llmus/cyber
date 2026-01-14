from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.dependencies import get_db
from app.llms.factories import build_llm_service
from app.llms.services import LLMService


async def get_llm_service(db: AsyncSession = Depends(get_db)) -> LLMService:
    return await build_llm_service(db)
