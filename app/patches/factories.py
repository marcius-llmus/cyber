from app.context.factories import build_codebase_service
from app.core.db import sessionmanager
from app.llms.factories import build_llm_service
from app.patches.repositories import DiffPatchRepository
from app.patches.services.diff_patches import DiffPatchService
from app.projects.factories import build_project_service
from sqlalchemy.ext.asyncio import AsyncSession


def build_diff_patch_repository(db: AsyncSession) -> DiffPatchRepository:
    return DiffPatchRepository(db)


async def build_diff_patch_service() -> DiffPatchService:
    return DiffPatchService(
        db=sessionmanager,
        diff_patch_repo_factory=build_diff_patch_repository,
        llm_service_factory=build_llm_service,
        project_service_factory=build_project_service,
        codebase_service_factory=build_codebase_service,
    )
