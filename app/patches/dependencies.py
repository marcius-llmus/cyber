from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.patches.factories import build_diff_patch_service
from app.patches.services import DiffPatchService


async def get_diff_patch_service(db: AsyncSession = Depends(get_db)) -> DiffPatchService:
    return await build_diff_patch_service(db)