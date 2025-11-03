from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, Response

from app.core.templating import templates
from app.settings.dependencies import get_settings_page_service, get_settings_service
from app.settings.exceptions import (
    ContextWindowExceededException,
    LLMSettingsNotFoundException,
    SettingsNotFoundException,
)
from app.settings.schemas import SettingsUpdate
from app.settings.services import SettingsPageService, SettingsService

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def get_settings_modal(
    request: Request,
    service: SettingsPageService = Depends(get_settings_page_service),
):
    try:
        page_data = service.get_settings_page_data()
    except SettingsNotFoundException as e:
        # This is a server error, as settings should always be initialized
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return templates.TemplateResponse(
        "settings/partials/modal_content.html", {"request": request, **page_data}
    )


@router.get("/api-key-input", response_class=HTMLResponse)
async def get_api_key_input(
    request: Request,
    model_name: str = Query(..., alias="coding_llm_settings.model_name"),
    service: SettingsPageService = Depends(get_settings_page_service),
):
    context = service.get_api_key_input_data(model_name)
    return templates.TemplateResponse(
        "settings/partials/api_key_input.html",
        {"request": request, **context},
    )


@router.post("/")
async def update_settings(
    request: Request,
    settings_in: SettingsUpdate,
    service: SettingsService = Depends(get_settings_service),
):
    try:
        service.update_settings(settings_in=settings_in)
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"HX-Trigger": "settingsSaved"})
    except (SettingsNotFoundException, LLMSettingsNotFoundException) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ContextWindowExceededException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
