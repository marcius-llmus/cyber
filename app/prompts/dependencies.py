from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.blueprints.dependencies import get_blueprint_service
from app.blueprints.services import BlueprintService
from app.commons.dependencies import get_db
from app.projects.dependencies import get_project_service
from app.projects.services import ProjectService
from app.prompts.repositories import PromptRepository
from app.prompts.services import PromptPageService, PromptService


async def get_prompt_repository(db: AsyncSession = Depends(get_db)) -> PromptRepository:
    return PromptRepository(db=db)


async def get_prompt_service(
    repo: PromptRepository = Depends(get_prompt_repository),
    project_service: ProjectService = Depends(get_project_service),
    blueprint_service: BlueprintService = Depends(get_blueprint_service),
) -> PromptService:
    return PromptService(
        prompt_repo=repo,
        project_service=project_service,
        blueprint_service=blueprint_service,
    )


async def get_prompt_page_service(
    prompt_service: PromptService = Depends(get_prompt_service),
    project_service: ProjectService = Depends(get_project_service),
    blueprint_service: BlueprintService = Depends(get_blueprint_service),
) -> PromptPageService:
    return PromptPageService(
        prompt_service=prompt_service,
        project_service=project_service,
        blueprint_service=blueprint_service,
    )
