from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from app.chat.dependencies import get_chat_service
from app.chat.services import ChatService
from app.commons.fastapi_htmx import htmx
from app.projects.exceptions import ActiveProjectRequiredException

router = APIRouter()

@router.post("/clear", response_class=HTMLResponse)
@htmx("chat/partials/message_list")
async def clear_chat(
    request: Request,
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        session = await chat_service.get_or_create_active_session()
        await chat_service.clear_session_messages(session_id=session.id)

        return {
            "messages": [],
            "session_id": session.id,
        }
    except ActiveProjectRequiredException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
