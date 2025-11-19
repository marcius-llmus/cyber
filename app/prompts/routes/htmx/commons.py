from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from app.commons.fastapi_htmx import htmx
from app.projects.exceptions import ActiveProjectRequiredException
from app.prompts.dependencies import get_prompt_service
from app.prompts.exceptions import PromptNotFoundException
from app.prompts.services import PromptService

router = APIRouter()


@router.post("/{prompt_id}/toggle-attachment", response_class=HTMLResponse)
@htmx("prompts/partials/prompt_item")
async def toggle_prompt_attachment(
    request: Request,
    prompt_id: int,
    service: PromptService = Depends(get_prompt_service),
):
    try:
        prompt, is_attached = await service.toggle_active_attachment_for_current_project(prompt_id=prompt_id)
        return {"prompt": prompt, "is_attached": is_attached}
    except PromptNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ActiveProjectRequiredException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))