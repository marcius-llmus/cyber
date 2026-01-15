"""Test fixtures.

These fixtures are intentionally scoped to tests under `tests/agents/` so the
agents app can evolve independently without leaking fixtures across domains.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.commons.dependencies import get_db
from app.core.db import Base
from app.main import app



pytest_plugins = [
    "tests.agents.fixtures",
    "tests.projects.fixtures",
    "tests.sessions.fixtures",
    "tests.settings.fixtures",
    "tests.llms.fixtures",
    "tests.chat.fixtures",
]

@pytest.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
async def setup_db(engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """
    Create database tables before tests run, and drop them after.
    """
    # Import all models here so SQLAlchemy registers them with Base.metadata
    from app.agents import models as agents_models  # noqa
    from app.chat import models as chat_models  # noqa
    from app.context import models as context_models  # noqa
    from app.llms import models as llms_models  # noqa
    from app.patches import models as patches_models  # noqa
    from app.projects import models as projects_models  # noqa
    from app.prompts import models as prompts_models  # noqa
    from app.sessions import models as sessions_models  # noqa
    from app.settings import models as settings_models  # noqa
    from app.usage import models as usage_models  # noqa

    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session")
def sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Async sessionmaker bound to the in-memory test engine."""
    return async_sessionmaker(engine, autocommit=False)


@pytest.fixture(scope="function")
async def db_session(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Provides a transactional session for each test function, rolling back at the end."""

    async with sessionmaker() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture(scope="function")
def client(db_session: AsyncSession) -> Generator[TestClient, None, None]:
    """
    Provides a TestClient with the database dependency overridden.
    """

    async def get_db_override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
