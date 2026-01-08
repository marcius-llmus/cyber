from app.patches.factories import build_diff_patch_service
from app.patches.services import DiffPatchService


async def get_diff_patch_service() -> DiffPatchService:
    return await build_diff_patch_service()
