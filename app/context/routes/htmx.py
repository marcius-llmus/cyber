from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.commons.fastapi_htmx import htmx
from app.context.dependencies import get_context_page_service, get_context_service
from app.context.schemas import ContextFileBatchUpdate
from app.context.services import ContextPageService, WorkspaceService
from app.core.templating import templates

router = APIRouter()


@router.get("/session/{session_id}/file-tree", response_class=HTMLResponse)
@htmx("context/partials/file_tree")
async def get_file_tree(
    request: Request,
    session_id: int,
    service: ContextPageService = Depends(get_context_page_service),
):
    page_data = await service.get_file_tree_page_data(session_id=session_id)
    return {**page_data}


@router.post("/session/{session_id}/files/batch", response_class=HTMLResponse)
async def batch_update_context_files(
    request: Request,
    session_id: int,
    data: ContextFileBatchUpdate,
    service: WorkspaceService = Depends(get_context_service),
    page_service: ContextPageService = Depends(get_context_page_service),
):
    await service.sync_files(session_id, data.filepaths)
    page_data = await page_service.get_context_files_page_data(session_id)
    return templates.TemplateResponse(
        "context/partials/context_file_list_items.html",
        {"request": request, **page_data}
    )


@router.delete("/session/{session_id}/files", response_class=HTMLResponse)
async def clear_all_context_files(
    request: Request,
    session_id: int,
    service: WorkspaceService = Depends(get_context_service),
    page_service: ContextPageService = Depends(get_context_page_service),
):
    await service.delete_context_for_session(session_id)
    page_data = await page_service.get_context_files_page_data(session_id)
    return templates.TemplateResponse(
        "context/partials/context_file_list_items.html",
        {"request": request, **page_data}
    )


@router.delete("/session/{session_id}/files/{context_file_id}", response_class=HTMLResponse)
async def remove_context_file(
    request: Request,
    session_id: int,
    context_file_id: int,
    service: WorkspaceService = Depends(get_context_service),
    page_service: ContextPageService = Depends(get_context_page_service),
):
    await service.remove_file(session_id, context_file_id)
    page_data = await page_service.get_context_files_page_data(session_id)
    return templates.TemplateResponse(
        "context/partials/context_file_list_items.html",
        {"request": request, **page_data}
    )
