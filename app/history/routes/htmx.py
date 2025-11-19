from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from app.commons.fastapi_htmx import htmx
from app.projects.exceptions import ActiveProjectRequiredException
from app.history.enums import HistoryEventType
from app.history.dependencies import get_history_page_service, get_history_service
from app.history.exceptions import ChatSessionNotFoundException
from app.history.services import HistoryPageService, HistoryService

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
@htmx("history/partials/session_list")
async def get_history_list(
    request: Request,
    service: HistoryPageService = Depends(get_history_page_service),
):
    page_data = await service.get_history_page_data()
    return {**page_data, "HistoryEventType": HistoryEventType}


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    request: Request,
    session_id: int,
    service: HistoryService = Depends(get_history_service),
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
        response.headers["HX-Trigger"] = HistoryEventType.SESSIONS_CHANGED
        return response

    except ChatSessionNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ActiveProjectRequiredException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))