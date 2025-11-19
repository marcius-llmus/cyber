from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import sessionmanager


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency that provides a transactional database session.
    """
    async with sessionmanager.session() as session:
        yield session
