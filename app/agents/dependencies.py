from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.commons.dependencies import get_db
from app.agents.repositories import WorkflowStateRepository
from app.agents.services import WorkflowService


async def build_workflow_service(db: AsyncSession) -> WorkflowService:
    repo = WorkflowStateRepository(db=db)
    return WorkflowService(workflow_repo=repo)


async def get_workflow_service(db: AsyncSession = Depends(get_db)) -> WorkflowService:
    return await build_workflow_service(db)
