from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from app.commons.fastapi_htmx import htmx
from app.projects.exceptions import ActiveProjectRequiredException
from app.sessions.enums import SessionEventType
from app.sessions.dependencies import get_session_page_service, get_session_service
from app.sessions.exceptions import ChatSessionNotFoundException
from app.sessions.services import SessionPageService, SessionService

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
@htmx("sessions/partials/session_list")
async def get_session_list(
    request: Request,
    service: SessionPageService = Depends(get_session_page_service),
):
    page_data = await service.get_sessions_page_data()
    return {**page_data, "SessionEventType": SessionEventType}


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    request: Request,
    session_id: int,
    service: SessionService = Depends(get_session_service),
):
    try:
        was_active = await service.delete_session(
            session_id_to_delete=session_id
        )

        if was_active:
            response = Response(status_code=status.HTTP_200_OK)
            response.headers["HX-Redirect"] = "/coder/"
            return response

        # A non-active session was deleted, just refresh the list.
        response = Response(status_code=status.HTTP_204_NO_CONTENT)
        response.headers["HX-Trigger"] = SessionEventType.SESSIONS_CHANGED
        return response

    except ChatSessionNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ActiveProjectRequiredException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))