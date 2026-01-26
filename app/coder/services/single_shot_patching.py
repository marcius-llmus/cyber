import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.coder.schemas import (
    CoderEvent,
    ContextFilesUpdatedEvent,
    LogLevel,
    SingleShotDiffAppliedEvent,
    WorkflowLogEvent,
)
from app.context.schemas import ContextFileListItem
from app.context.services import WorkspaceService
from app.core.db import DatabaseSessionManager
from app.patches.enums import DiffPatchStatus, PatchProcessorType

logger = logging.getLogger(__name__)


class SingleShotPatchService:
    def __init__(
        self,
        *,
        db: DatabaseSessionManager,
        diff_patch_service_factory: Callable[[], Awaitable[Any]],
        context_service_factory: Callable[[AsyncSession], Awaitable[WorkspaceService]],
    ) -> None:
        self.db = db
        self.diff_patch_service_factory = diff_patch_service_factory
        self.context_service_factory = context_service_factory

    async def apply_from_blocks(
        self,
        *,
        session_id: int,
        turn_id: str,
        blocks: list[dict[str, Any]],
        processor_type: PatchProcessorType = PatchProcessorType.UDIFF_LLM,
    ) -> AsyncGenerator[CoderEvent]:
        diff_patch_service = await self.diff_patch_service_factory()

        representations: list[Any] = []

        extracted = diff_patch_service.extract_diffs_from_blocks(
            turn_id=turn_id,
            session_id=session_id,
            blocks=blocks,
            processor_type=processor_type,
        )

        for diff_patch in extracted:
            result = await diff_patch_service.process_diff(diff_patch)
            if result.status != DiffPatchStatus.APPLIED:
                continue

            representation = result.representation
            if not (representation and representation.patches):
                continue

            representations.append(representation)

            for patch in representation.patches:
                yield SingleShotDiffAppliedEvent(
                    file_path=patch.path, output=str(result)
                )

        if not representations:
            return

        async with self.db.session() as session:
            context_service = await self.context_service_factory(session)

            for representation in representations:
                for patch in representation.patches:
                    if not (
                        patch.is_added_file or patch.is_removed_file or patch.is_rename
                    ):
                        continue

                    try:
                        await context_service.sync_context_for_diff(
                            session_id=session_id,
                            patch=patch,
                        )
                    except Exception as e:
                        yield WorkflowLogEvent(
                            message=(
                                "Failed to sync context from diff "
                                f"(session_id={session_id}): {e}"
                            ),
                            level=LogLevel.ERROR,
                        )

            files = await context_service.get_active_context(session_id)
            files_data = [
                ContextFileListItem(id=f.id, file_path=f.file_path) for f in files
            ]

        yield ContextFilesUpdatedEvent(session_id=session_id, files=files_data)

        logger.info(
            "Processed %s SINGLE_SHOT diff patch(es) for turn_id=%s session_id=%s",
            len(representations),
            turn_id,
            session_id,
        )
