from collections.abc import AsyncGenerator, AsyncIterator, Generator
from contextlib import asynccontextmanager
from unittest.mock import create_autospec

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
from app.core.db import Base, DatabaseSessionManager
from app.main import app

pytest_plugins = [
    "tests.agents.fixtures",
    "tests.projects.fixtures",
    "tests.sessions.fixtures",
    "tests.settings.fixtures",
    "tests.llms.fixtures",
    "tests.chat.fixtures",
    "tests.context.fixtures",
    "tests.patches.fixtures",
    "tests.coder.fixtures",
]


@pytest.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
async def setup_db(engine: AsyncEngine) -> AsyncGenerator[None]:
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
) -> AsyncGenerator[AsyncSession]:
    """Provides a transactional session for each test function, rolling back at the end."""

    async with sessionmaker() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture(scope="function")
def db_session_mock() -> AsyncSession:
    """Lightweight AsyncSession mock for wiring/unit tests (deps/factories)."""
    return create_autospec(AsyncSession, instance=True)


@pytest.fixture(scope="function")
def db_sessionmanager_mock(
    mocker,
    db_session_mock: AsyncSession,
) -> DatabaseSessionManager:
    """DatabaseSessionManager mock whose .session() yields db_session_mock."""

    db = mocker.create_autospec(DatabaseSessionManager, instance=True)

    @asynccontextmanager
    async def _session() -> AsyncIterator[AsyncSession]:
        yield db_session_mock

    db.session = _session  # type: ignore[method-assign]
    return db


@pytest.fixture(scope="function")
def client(db_session_mock: AsyncSession) -> Generator[TestClient]:
    """
    Provides a TestClient with the database dependency overridden.
    """

    # here I am mocking lifespan because it is not really needed for request
    # in case in the future we start needing it, we can set up a semi-real one
    @asynccontextmanager
    async def mock_lifespan(_app):  # noqa: ANN001
        yield

    app.router.lifespan_context = mock_lifespan

    async def get_db_override() -> AsyncGenerator[AsyncSession]:
        yield db_session_mock

    app.dependency_overrides[get_db] = get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
