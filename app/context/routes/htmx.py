from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from app.commons.fastapi_htmx import htmx

from app.context.dependencies import get_context_page_service
from app.context.services import ContextPageService

router = APIRouter()


@router.get("/file-tree", response_class=HTMLResponse)
@htmx("context/partials/file_tree")
async def get_file_tree(
    request: Request,
    service: ContextPageService = Depends(get_context_page_service),
):
    page_data = await service.get_file_tree_page_data()
    return page_data