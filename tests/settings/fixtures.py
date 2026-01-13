from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings.models import Settings


@pytest.fixture
async def settings(db_session: AsyncSession) -> Settings:
    """Creates a default singleton Settings record."""
    db_obj = Settings(
        id=1,
        max_history_length=50,
        ast_token_limit=10_000,
        grep_token_limit=4_000,
        diff_patches_auto_open=True,
        diff_patches_auto_apply=True,
        coding_llm_temperature=Decimal("0.7"),
    )
    db_session.add(db_obj)
    await db_session.flush()
    await db_session.refresh(db_obj)
    return db_obj
