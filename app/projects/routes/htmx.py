from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse

from app.chat.dependencies import get_chat_service
from app.chat.services import ChatService
from app.commons.fastapi_htmx import htmx
from app.projects.dependencies import get_project_page_service, get_project_service
from app.projects.exceptions import ProjectNotFoundException
from app.projects.services import ProjectPageService, ProjectService

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
@htmx("projects/partials/project_list")
async def get_project_list(
    request: Request,  # noqa: ARG001
    service: ProjectPageService = Depends(get_project_page_service),
):
    page_data = await service.get_projects_page_data()
    return page_data


@router.put("/{project_id}/activate", response_class=HTMLResponse)
@htmx("projects/partials/project_list")
async def set_active_project(
    request: Request,  # noqa: ARG001
    project_id: int,
    service: ProjectService = Depends(get_project_service),
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        await service.set_active_project(project_id=project_id)
        session = await chat_service.get_or_create_session_for_project(
            project_id=project_id
        )

        response = Response(status_code=status.HTTP_200_OK)
        response.headers["HX-Redirect"] = f"/coder/session/{session.id}"
        return response
    except ProjectNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
