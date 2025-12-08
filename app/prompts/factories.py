from sqlalchemy.ext.asyncio import AsyncSession

from app.projects.factories import build_project_service
from app.prompts.repositories import PromptRepository
from app.prompts.services import PromptService


async def build_prompt_service(db: AsyncSession) -> PromptService:
    repo = PromptRepository(db)
    project_service = await build_project_service(db)
    return PromptService(prompt_repo=repo, project_service=project_service)
