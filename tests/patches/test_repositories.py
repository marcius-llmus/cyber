"""Repository tests for the patches app."""

from datetime import datetime, timedelta

import pytest

from app.patches.enums import DiffPatchStatus, PatchProcessorType
from app.patches.models import DiffPatch
from app.patches.schemas import DiffPatchInternalCreate


class TestDiffPatchRepository:
    async def test_list_pending_by_turn_filters_and_orders(
        self,
        diff_patch_repository,
        db_session,
        chat_session,
    ):
        """Should return only PENDING patches for given (session_id, turn_id) ordered by created_at asc."""
        turn_id = "t1"
        created1 = await diff_patch_repository.create(
            obj_in=DiffPatchInternalCreate(
                session_id=chat_session.id,
                turn_id=turn_id,
                diff="d1",
                processor_type=PatchProcessorType.UDIFF_LLM,
                status=DiffPatchStatus.PENDING,
            )
        )
        created2 = await diff_patch_repository.create(
            obj_in=DiffPatchInternalCreate(
                session_id=chat_session.id,
                turn_id=turn_id,
                diff="d2",
                processor_type=PatchProcessorType.UDIFF_LLM,
                status=DiffPatchStatus.PENDING,
            )
        )

        # Ensure ordering by created_at by nudging timestamps if SQLite resolution is coarse.
        created1.created_at = datetime.utcnow() - timedelta(seconds=10)
        created2.created_at = datetime.utcnow()
        await db_session.flush()

        pending = await diff_patch_repository.list_pending_by_turn(
            session_id=chat_session.id, turn_id=turn_id
        )

        assert [p.id for p in pending] == [created1.id, created2.id]
        assert all(p.status == DiffPatchStatus.PENDING for p in pending)

    async def test_list_pending_by_turn_excludes_non_pending_statuses(
        self,
        diff_patch_repository,
        db_session,
        chat_session,
    ):
        """Should exclude APPLIED/FAILED/REJECTED patches even if turn_id matches."""
        turn_id = "t1"
        await diff_patch_repository.create(
            obj_in=DiffPatchInternalCreate(
                session_id=chat_session.id,
                turn_id=turn_id,
                diff="pending",
                processor_type=PatchProcessorType.UDIFF_LLM,
                status=DiffPatchStatus.PENDING,
            )
        )
        await diff_patch_repository.create(
            obj_in=DiffPatchInternalCreate(
                session_id=chat_session.id,
                turn_id=turn_id,
                diff="applied",
                processor_type=PatchProcessorType.UDIFF_LLM,
                status=DiffPatchStatus.APPLIED,
            )
        )
        await diff_patch_repository.create(
            obj_in=DiffPatchInternalCreate(
                session_id=chat_session.id,
                turn_id=turn_id,
                diff="failed",
                processor_type=PatchProcessorType.UDIFF_LLM,
                status=DiffPatchStatus.FAILED,
            )
        )
        await diff_patch_repository.create(
            obj_in=DiffPatchInternalCreate(
                session_id=chat_session.id,
                turn_id=turn_id,
                diff="rejected",
                processor_type=PatchProcessorType.UDIFF_LLM,
                status=DiffPatchStatus.REJECTED,
            )
        )

        pending = await diff_patch_repository.list_pending_by_turn(
            session_id=chat_session.id, turn_id=turn_id
        )
        assert [p.diff for p in pending] == ["pending"]

    async def test_list_pending_by_turn_excludes_other_turns_and_sessions(
        self,
        diff_patch_repository,
        db_session,
        chat_session,
    ):
        """Should only return rows for the exact (session_id, turn_id)."""
        await diff_patch_repository.create(
            obj_in=DiffPatchInternalCreate(
                session_id=chat_session.id,
                turn_id="t1",
                diff="target",
                processor_type=PatchProcessorType.UDIFF_LLM,
                status=DiffPatchStatus.PENDING,
            )
        )
        await diff_patch_repository.create(
            obj_in=DiffPatchInternalCreate(
                session_id=chat_session.id,
                turn_id="t2",
                diff="other_turn",
                processor_type=PatchProcessorType.UDIFF_LLM,
                status=DiffPatchStatus.PENDING,
            )
        )
        await diff_patch_repository.create(
            obj_in=DiffPatchInternalCreate(
                session_id=chat_session.id + 999,
                turn_id="t1",
                diff="other_session",
                processor_type=PatchProcessorType.UDIFF_LLM,
                status=DiffPatchStatus.PENDING,
            )
        )

        pending = await diff_patch_repository.list_pending_by_turn(
            session_id=chat_session.id, turn_id="t1"
        )
        assert [p.diff for p in pending] == ["target"]

    async def test_list_by_turn_filters_and_orders(
        self,
        diff_patch_repository,
        db_session,
        chat_session,
    ):
        """Should return all patches for given (session_id, turn_id) ordered by created_at asc."""
        turn_id = "t1"
        created1 = await diff_patch_repository.create(
            obj_in=DiffPatchInternalCreate(
                session_id=chat_session.id,
                turn_id=turn_id,
                diff="d1",
                processor_type=PatchProcessorType.UDIFF_LLM,
                status=DiffPatchStatus.PENDING,
            )
        )
        created2 = await diff_patch_repository.create(
            obj_in=DiffPatchInternalCreate(
                session_id=chat_session.id,
                turn_id=turn_id,
                diff="d2",
                processor_type=PatchProcessorType.UDIFF_LLM,
                status=DiffPatchStatus.APPLIED,
            )
        )

        created1.created_at = datetime.utcnow() - timedelta(seconds=10)
        created2.created_at = datetime.utcnow()
        await db_session.flush()

        rows = await diff_patch_repository.list_by_turn(
            session_id=chat_session.id, turn_id=turn_id
        )
        assert [p.id for p in rows] == [created1.id, created2.id]

    async def test_list_by_turn_returns_empty_when_none(self, diff_patch_repository):
        """Should return [] when there are no patches for given (session_id, turn_id)."""
        rows = await diff_patch_repository.list_by_turn(session_id=1, turn_id="t")
        assert rows == []

    async def test_list_by_turn_does_not_filter_status(self, diff_patch_repository, chat_session):
        """list_by_turn should include all statuses."""
        await diff_patch_repository.create(
            obj_in=DiffPatchInternalCreate(
                session_id=chat_session.id,
                turn_id="t1",
                diff="pending",
                processor_type=PatchProcessorType.UDIFF_LLM,
                status=DiffPatchStatus.PENDING,
            )
        )
        await diff_patch_repository.create(
            obj_in=DiffPatchInternalCreate(
                session_id=chat_session.id,
                turn_id="t1",
                diff="applied",
                processor_type=PatchProcessorType.UDIFF_LLM,
                status=DiffPatchStatus.APPLIED,
            )
        )
        rows = await diff_patch_repository.list_by_turn(session_id=chat_session.id, turn_id="t1")
        assert {p.status for p in rows} == {DiffPatchStatus.PENDING, DiffPatchStatus.APPLIED}

    async def test_list_pending_by_turn_returns_empty_when_no_pending(self, diff_patch_repository, chat_session):
        """list_pending_by_turn should return [] when there are no pending rows."""
        await diff_patch_repository.create(
            obj_in=DiffPatchInternalCreate(
                session_id=chat_session.id,
                turn_id="t1",
                diff="applied",
                processor_type=PatchProcessorType.UDIFF_LLM,
                status=DiffPatchStatus.APPLIED,
            )
        )
        rows = await diff_patch_repository.list_pending_by_turn(session_id=chat_session.id, turn_id="t1")
        assert rows == []