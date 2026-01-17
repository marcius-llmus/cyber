from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from app.commons.fastapi_htmx import htmx
from app.projects.exceptions import ActiveProjectRequiredException
from app.prompts.dependencies import get_prompt_page_service, get_prompt_service
from app.prompts.enums import PromptEventType
from app.prompts.exceptions import PromptNotFoundException
from app.prompts.schemas import BlueprintRequest
from app.prompts.services import PromptPageService, PromptService

router = APIRouter()


@router.delete("/blueprint-prompt")
async def delete_blueprint_prompt(  # noqa: ARG001
    request: Request,
    service: PromptService = Depends(get_prompt_service),
):
    try:
        await service.delete_project_blueprint_prompt()
    except PromptNotFoundException:
        pass  # If it doesn't exist, we don't need to do anything.
    except ActiveProjectRequiredException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    response = HTMLResponse(status_code=status.HTTP_204_NO_CONTENT)
    response.headers["HX-Trigger"] = PromptEventType.BLUEPRINTS_CHANGED
    return response


@router.post("/from-blueprint", response_class=HTMLResponse)
@htmx("prompts/partials/blueprint_list")
async def create_prompt_from_blueprint(
    request: Request,  # noqa: ARG001
    blueprint_in: BlueprintRequest,
    service: PromptService = Depends(get_prompt_service),
    page_service: PromptPageService = Depends(get_prompt_page_service),
):
    try:
        await service.create_or_update_project_blueprint_prompt(path=blueprint_in.path)
        return await page_service.get_blueprint_prompts_list_data()
    except ActiveProjectRequiredException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/blueprint/list", response_class=HTMLResponse)
@htmx("prompts/partials/blueprint_list")
async def get_blueprint_list(
    request: Request,  # noqa: ARG001
    page_service: PromptPageService = Depends(get_prompt_page_service),
):
    return await page_service.get_blueprint_prompts_list_data()
