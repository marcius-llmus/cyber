from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse

from app.commons.fastapi_htmx import htmx
from app.core.templating import templates
from app.blueprints.dependencies import get_blueprint_service
from app.blueprints.services import BlueprintService
from app.projects.exceptions import ActiveProjectRequiredException
from app.prompts.dependencies import get_prompt_page_service, get_prompt_service
from app.prompts.enums import PromptTargetSelector
from app.prompts.exceptions import PromptNotFoundException
from app.prompts.schemas import BlueprintRequest, PromptCreate, PromptUpdate
from app.prompts.services import PromptPageService, PromptService

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def get_prompts_modal(
    request: Request,
    service: PromptPageService = Depends(get_prompt_page_service),
):
    page_data = service.get_prompts_page_data()
    return templates.TemplateResponse(
        "prompts/partials/modal_content.html", {"request": request, **page_data}
    )


@router.get("/new/global", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_form")
async def get_new_global_prompt_form(
    request: Request,
    service: PromptPageService = Depends(get_prompt_page_service),
):
    context = service.get_new_global_prompt_form_context()
    return context


@router.get("/new/project", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_form")
async def get_new_project_prompt_form(
    request: Request,
    service: PromptPageService = Depends(get_prompt_page_service),
):
    try:
        context = service.get_new_project_prompt_form_context()
        return context
    except ActiveProjectRequiredException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/global", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_list")
async def create_global_prompt(
    request: Request,
    prompt_in: PromptCreate,
    service: PromptService = Depends(get_prompt_service),
    page_service: PromptPageService = Depends(get_prompt_page_service),
):
    service.create_prompt(prompt_in=prompt_in)
    return page_service.get_global_prompts_list_data()


@router.post("/project", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_list")
async def create_project_prompt(
    request: Request,
    prompt_in: PromptCreate,
    service: PromptService = Depends(get_prompt_service),
    page_service: PromptPageService = Depends(get_prompt_page_service),
):
    service.create_prompt(prompt_in=prompt_in)
    return page_service.get_project_prompts_list_data()


@router.get("/global/{prompt_id}/edit", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_form")
async def get_edit_global_prompt_form( # note: this "edit" is a related to the form, not to the endpoint
    request: Request,
    prompt_id: int,
    page_service: PromptPageService = Depends(get_prompt_page_service),
):
    try:
        context = page_service.get_edit_global_prompt_form_context(prompt_id=prompt_id)
        return context
    except PromptNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/project/{prompt_id}/edit", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_form")
async def get_edit_project_prompt_form(
    request: Request,
    prompt_id: int,
    page_service: PromptPageService = Depends(get_prompt_page_service),
):
    try:
        context = page_service.get_edit_project_prompt_form_context(prompt_id=prompt_id)
        return context
    except PromptNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/global/{prompt_id}", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_list")
async def update_global_prompt(
    request: Request,
    prompt_id: int,
    prompt_in: PromptUpdate,
    service: PromptService = Depends(get_prompt_service),
    page_service: PromptPageService = Depends(get_prompt_page_service),
):
    try:
        service.update_prompt(prompt_id=prompt_id, prompt_in=prompt_in)
        return page_service.get_global_prompts_list_data()
    except PromptNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/project/{prompt_id}", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_list")
async def update_project_prompt(
    request: Request,
    prompt_id: int,
    prompt_in: PromptUpdate,
    service: PromptService = Depends(get_prompt_service),
    page_service: PromptPageService = Depends(get_prompt_page_service),
):
    try:
        service.update_prompt(prompt_id=prompt_id, prompt_in=prompt_in)
        return page_service.get_project_prompts_list_data()
    except PromptNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/blueprint-prompt")
async def delete_blueprint_prompt(
    request: Request,
    service: PromptService = Depends(get_prompt_service),
):
    try:
        service.delete_project_blueprint_prompt()
    except PromptNotFoundException:
        pass  # If it doesn't exist, we don't need to do anything.
    except ActiveProjectRequiredException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    response = HTMLResponse(status_code=status.HTTP_204_NO_CONTENT)
    response.headers["HX-Trigger"] = "refreshBlueprints"
    return response


@router.delete("/global/{prompt_id}", status_code=status.HTTP_200_OK)
async def delete_global_prompt(
    prompt_id: int,
    service: PromptService = Depends(get_prompt_service),
):
    try:
        service.delete_prompt(prompt_id=prompt_id)
        return Response(status_code=status.HTTP_200_OK)
    except PromptNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/project/{prompt_id}", status_code=status.HTTP_200_OK)
async def delete_project_prompt(
    prompt_id: int,
    service: PromptService = Depends(get_prompt_service),
):
    try:
        service.delete_prompt(prompt_id=prompt_id)
        return Response(status_code=status.HTTP_200_OK)
    except PromptNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{prompt_id}/toggle-attachment", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_item")
async def toggle_prompt_attachment(
    request: Request,
    prompt_id: int,
    service: PromptService = Depends(get_prompt_service),
):
    try:
        prompt, is_attached = service.toggle_project_attachment(prompt_id=prompt_id)
        return {"prompt": prompt, "is_attached": is_attached}
    except PromptNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ActiveProjectRequiredException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/from-blueprint", response_class=HTMLResponse)
@htmx("prompts/partials/blueprint_prompt_item")
async def create_prompt_from_blueprint(
    request: Request,
    blueprint_in: BlueprintRequest,
    service: PromptService = Depends(get_prompt_service),
):
    try:
        prompt, _ = service.create_or_update_project_blueprint_prompt(path=blueprint_in.path)
        return {"prompt": prompt}
    except ActiveProjectRequiredException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/blueprints", response_class=HTMLResponse)
@htmx("prompts/partials/blueprint_generator")
async def get_blueprint_generator(
    request: Request,
    blueprint_service: BlueprintService = Depends(get_blueprint_service),
):
    blueprints = blueprint_service.list_blueprints()
    return {"blueprints": blueprints}
