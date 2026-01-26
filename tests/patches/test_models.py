"""Model tests for the patches app."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.patches.enums import DiffPatchStatus, PatchProcessorType
from app.patches.models import DiffPatch


class TestDiffPatchModel:
    async def test_diff_patch_can_be_persisted(self, db_session, chat_session):
        """DiffPatch should be insertable with required fields."""
        patch = DiffPatch(
            session_id=chat_session.id,
            turn_id="t1",
            diff="--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-hi\n+hello\n",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        db_session.add(patch)
        await db_session.flush()

        retrieved = await db_session.get(DiffPatch, patch.id)
        assert retrieved is not None
        assert retrieved.turn_id == "t1"
        assert retrieved.session_id == chat_session.id
        assert retrieved.processor_type == PatchProcessorType.UDIFF_LLM

    async def test_diff_patch_requires_diff(self, db_session, chat_session):
        """DiffPatch.diff is non-nullable; missing diff should error on flush."""
        patch = DiffPatch(
            session_id=chat_session.id,
            turn_id="t1",
            diff=None,
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        db_session.add(patch)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_diff_patch_requires_processor_type(self, db_session, chat_session):
        """DiffPatch.processor_type is non-nullable; missing should error on flush."""
        patch = DiffPatch(
            session_id=chat_session.id,
            turn_id="t1",
            diff="x",
            processor_type=None,
        )
        db_session.add(patch)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_diff_patch_requires_turn_id(self, db_session, chat_session):
        """DiffPatch.turn_id is non-nullable; missing should error on flush."""
        patch = DiffPatch(
            session_id=chat_session.id,
            turn_id=None,
            diff="x",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        db_session.add(patch)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_diff_patch_defaults_status_pending(self, db_session, chat_session):
        """DiffPatch.status should default to PENDING when not explicitly set."""
        patch = DiffPatch(
            session_id=chat_session.id,
            turn_id="t1",
            diff="x",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        db_session.add(patch)
        await db_session.flush()
        await db_session.refresh(patch)

        assert patch.status == DiffPatchStatus.PENDING

    async def test_diff_patch_fk_cascade_on_delete(self, db_session, chat_session):
        """DiffPatch rows should be deleted when ChatSession is deleted (ON DELETE CASCADE)."""
        patch = DiffPatch(
            session_id=chat_session.id,
            turn_id="t1",
            diff="x",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        db_session.add(patch)
        await db_session.flush()

        patch_id = patch.id
        assert await db_session.get(DiffPatch, patch_id) is not None

        await db_session.delete(chat_session)
        await db_session.flush()
        db_session.expire_all()

        assert await db_session.get(DiffPatch, patch_id) is None

    async def test_diff_patch_has_created_at_timestamp(self, db_session, chat_session):
        """DiffPatch.created_at should be set by the database."""
        patch = DiffPatch(
            session_id=chat_session.id,
            turn_id="t1",
            diff="x",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        db_session.add(patch)
        await db_session.flush()
        await db_session.refresh(patch)
        assert patch.created_at is not None

    async def test_diff_patch_updated_at_updates_on_update(
        self, db_session, chat_session
    ):
        """DiffPatch.updated_at should change when row is updated."""
        patch = DiffPatch(
            session_id=chat_session.id,
            turn_id="t1",
            diff="x",
            processor_type=PatchProcessorType.UDIFF_LLM,
        )
        db_session.add(patch)
        await db_session.flush()
        await db_session.refresh(patch)

        assert patch.updated_at is None

        patch.error_message = "err"
        await db_session.flush()
        await db_session.refresh(patch)

        stmt = select(DiffPatch).where(DiffPatch.id == patch.id)
        result = await db_session.execute(stmt)
        retrieved = result.scalar_one()
        assert retrieved.updated_at is not None