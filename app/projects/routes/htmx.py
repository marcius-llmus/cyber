from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from app.commons.fastapi_htmx import htmx

from app.projects.dependencies import get_project_page_service, get_project_service
from app.projects.exceptions import ProjectNotFoundException
from app.projects.services import ProjectPageService, ProjectService

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
@htmx("projects/partials/project_list")
async def get_project_list(
    request: Request,
    service: ProjectPageService = Depends(get_project_page_service),
):
    page_data = service.get_projects_page_data()
    return page_data


@router.put("/{project_id}/activate", response_class=HTMLResponse)
@htmx("projects/partials/project_list")
async def set_active_project(
    request: Request,
    project_id: int,
    service: ProjectService = Depends(get_project_service),
):
    try:
        projects = service.set_active_project(project_id=project_id)
        return {"projects": projects}
    except ProjectNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))