from fastapi import HTTPException, status, APIRouter, Depends, WebSocket, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.chat.services import ChatService
from app.chat.dependencies import get_chat_service
from app.coder.dependencies import (
    get_coder_page_service,
    CoderPageService,
)
from app.coder.presentation import WebSocketOrchestrator
from app.commons.websockets import WebSocketConnectionManager
from app.core.templating import templates
from app.history.exceptions import ChatSessionNotFoundException
from app.history.services import HistoryService
from app.history.dependencies import get_history_service

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def redirect_to_session(
    chat_service: ChatService = Depends(get_chat_service),
):
    session = chat_service.get_or_create_active_session()
    return RedirectResponse(url=f"session/{session.id}")


@router.get("/session/{session_id}", response_class=HTMLResponse)
async def read_session(
    request: Request,
    session_id: int,
    page_service: CoderPageService = Depends(get_coder_page_service),
    history_service: HistoryService = Depends(get_history_service),
):
    try:
        history_service.set_active_session(session_id=session_id)
        page_data = page_service.get_main_page_data(session_id=session_id)
        return templates.TemplateResponse(
            "chat/pages/main.html", {"request": request, **page_data}
        )
    except ChatSessionNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.websocket("/ws/session/{session_id}", name="conversation_websocket")
async def conversation_websocket(
    websocket: WebSocket,
    session_id: int,
):
    ws_manager = WebSocketConnectionManager(websocket)
    await ws_manager.connect()
    orchestrator = WebSocketOrchestrator(ws_manager=ws_manager, session_id=session_id)
    await orchestrator.handle_connection()