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


@router.get("/form", response_class=HTMLResponse)
async def get_settings_form(
    request: Request,
    service: SettingsPageService = Depends(get_settings_page_service),
):
    try:
        page_data = await service.get_settings_page_data()
    except SettingsNotFoundException as e:
        # This is a server error, as settings should always be initialized
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    return templates.TemplateResponse(
        "settings/partials/settings_form.html", {"request": request, **page_data}
    )


@router.get("/api-key-input", response_class=HTMLResponse)
async def get_api_key_input(
    request: Request,
    coding_llm_settings_id: int = Query(...),
    service: SettingsPageService = Depends(get_settings_page_service),
):
    context = await service.get_api_key_input_data_by_id(coding_llm_settings_id)
    return templates.TemplateResponse(
        "settings/partials/api_key_input.html",
        {"request": request, **context},
    )


@router.post("/")
async def update_settings(
    request: Request,  # noqa: ARG001
    settings_in: SettingsUpdate,
    service: SettingsService = Depends(get_settings_service),
):
    try:
        await service.update_settings(settings_in=settings_in)
        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
            headers={"HX-Trigger": "settingsSaved"},
        )
    except (SettingsNotFoundException, LLMSettingsNotFoundException) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ContextWindowExceededException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
