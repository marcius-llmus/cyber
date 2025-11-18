import contextlib
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import sessionmanager


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency that provides a transactional database session.
    """
    async with sessionmanager.session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@contextlib.asynccontextmanager
async def db_session_manager() -> AsyncIterator[AsyncSession]:
    """
    Context manager for a transactional database session, for use in non-request contexts like WebSockets.
    """
    async with sessionmanager.session() as session:
        yield session