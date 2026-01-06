from sqlalchemy.ext.asyncio import AsyncSession

from app.context.factories import build_codebase_service
from app.llms.factories import build_llm_service
from app.projects.factories import build_project_service
from app.patches.repositories import DiffPatchRepository
from app.patches.services.diff_patches import DiffPatchService
from app.settings.factories import build_settings_service


async def build_diff_patch_service(db: AsyncSession) -> DiffPatchService:
    repo = DiffPatchRepository(db=db)
    llm_service = await build_llm_service(db)
    project_service = await build_project_service(db)
    codebase_service = await build_codebase_service()
    settings_service = await build_settings_service(db)
    return DiffPatchService(
        diff_patch_repo=repo,
        llm_service=llm_service,
        project_service=project_service,
        codebase_service=codebase_service,
        settings_service=settings_service,
    )