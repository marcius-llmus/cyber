from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse

from app.commons.fastapi_htmx import htmx
from app.projects.exceptions import ActiveProjectRequiredException
from app.prompts.dependencies import get_prompt_page_service, get_prompt_service
from app.prompts.exceptions import PromptNotFoundException
from app.prompts.schemas import PromptCreate, PromptUpdate
from app.prompts.services import PromptPageService, PromptService

router = APIRouter()


@router.get("/new/project", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_form")
async def get_new_project_prompt_form(
    request: Request,
    page_service: PromptPageService = Depends(get_prompt_page_service),
):
    try:
        context = await page_service.get_new_project_prompt_form_context()
        return context
    except ActiveProjectRequiredException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/project/list", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_list")
async def get_project_prompts_list(
    request: Request,
    page_service: PromptPageService = Depends(get_prompt_page_service),
):
    return await page_service.get_project_prompts_list_data()


@router.post("/project", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_item")
async def create_project_prompt(
    request: Request,
    prompt_in: PromptCreate,
    service: PromptService = Depends(get_prompt_service),
    page_service: PromptPageService = Depends(get_prompt_page_service),
):
    try:
        new_prompt = await service.create_project_prompt(prompt_in=prompt_in)
        context = await page_service.get_prompt_view_context(prompt_id=new_prompt.id)
        return context
    except ActiveProjectRequiredException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/project/{prompt_id}/edit", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_form")
async def get_edit_project_prompt_form(
    request: Request,
    prompt_id: int,
    page_service: PromptPageService = Depends(get_prompt_page_service),
):
    try:
        context = await page_service.get_edit_project_prompt_form_context(prompt_id=prompt_id)
        return context
    except PromptNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/project/{prompt_id}/view", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_item")
async def get_project_prompt_view(
    request: Request,
    prompt_id: int,
    page_service: PromptPageService = Depends(get_prompt_page_service),
):
    try:
        context = await page_service.get_prompt_view_context(prompt_id=prompt_id)
        return context
    except PromptNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/project/{prompt_id}", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_item")
async def update_project_prompt(
    request: Request,
    prompt_id: int,
    prompt_in: PromptUpdate,
    service: PromptService = Depends(get_prompt_service),
    page_service: PromptPageService = Depends(get_prompt_page_service),
):
    try:
        await service.update_prompt(prompt_id=prompt_id, prompt_in=prompt_in)
        context = await page_service.get_prompt_view_context(prompt_id=prompt_id)
        return context
    except PromptNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/project/{prompt_id}")
async def delete_project_prompt(
    prompt_id: int,
    service: PromptService = Depends(get_prompt_service),
):
    try:
        await service.delete_prompt(prompt_id=prompt_id)
        return Response(status_code=status.HTTP_200_OK)
    except PromptNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
