from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.factories import build_workflow_service
from app.commons.dependencies import get_db
from app.agents.services import WorkflowService


async def get_workflow_service(db: AsyncSession = Depends(get_db)) -> WorkflowService:
    return await build_workflow_service(db)
