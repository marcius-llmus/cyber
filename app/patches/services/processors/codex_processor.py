import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

from apply_patch_py import apply_patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.services.codebase import CodebaseService
from app.core.db import DatabaseSessionManager
from app.llms.services import LLMService
from app.patches.repositories import DiffPatchRepository
from app.patches.services.processors import BasePatchProcessor
from app.projects.exceptions import ActiveProjectRequiredException
from app.projects.services import ProjectService

logger = logging.getLogger(__name__)


class CodexProcessor(BasePatchProcessor):
    def __init__(
        self,
        *,
        db: DatabaseSessionManager,
        diff_patch_repo_factory: Callable[[AsyncSession], DiffPatchRepository],
        llm_service_factory: Callable[[AsyncSession], Awaitable[LLMService]],
        project_service_factory: Callable[[AsyncSession], Awaitable[ProjectService]],
        codebase_service_factory: Callable[[], Awaitable[CodebaseService]],
    ):
        self.db = db
        self.diff_patch_repo_factory = diff_patch_repo_factory
        self.llm_service_factory = llm_service_factory
        self.project_service_factory = project_service_factory
        self.codebase_service_factory = codebase_service_factory

    async def apply_patch(self, diff: str) -> None:
        async with self.db.session() as session:
            project_service = await self.project_service_factory(session)
            project = await project_service.get_active_project()
            if not project:
                raise ActiveProjectRequiredException(
                    "Active project required to apply patches."
                )
            affected = await apply_patch(diff, workdir=Path(project.path))
            if not affected.success:
                raise ValueError(f"Failed to apply patch: {affected}")
