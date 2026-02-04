from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.chat.dependencies import get_chat_service
from app.chat.services import ChatService
from app.coder.dependencies import (
    CoderPageService,
    get_active_run_registry,
    get_coder_page_service,
    get_coder_service,
)
from app.coder.presentation import WebSocketOrchestrator
from app.coder.services import CoderService
from app.coder.services.active_runs import ActiveRunRegistry
from app.commons.websockets import WebSocketConnectionManager
from app.commons.fastapi_htmx import htmx
from app.core.templating import templates
from app.projects.exceptions import ActiveProjectRequiredException
from app.sessions.dependencies import get_session_service
from app.sessions.exceptions import ChatSessionNotFoundException
from app.sessions.services import SessionService

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def redirect_to_session(
    request: Request,
    chat_service: ChatService = Depends(get_chat_service),
    page_service: CoderPageService = Depends(get_coder_page_service),
):
    try:
        session = await chat_service.get_or_create_active_session()
        return RedirectResponse(url=f"session/{session.id}")
    except ActiveProjectRequiredException:
        page_data = await page_service.get_main_page_data(session_id=None)
        return templates.TemplateResponse(
            "projects/pages/no_active_project.html",
            {"request": request, "session": None, **page_data},
        )


@router.get("/session/{session_id}", response_class=HTMLResponse)
async def read_session(
    request: Request,
    session_id: int,
    page_service: CoderPageService = Depends(get_coder_page_service),
    session_service: SessionService = Depends(get_session_service),
):
    try:
        await session_service.set_active_session(session_id=session_id)
        page_data = await page_service.get_main_page_data(session_id=session_id)
        return templates.TemplateResponse(
            "chat/pages/main.html", {"request": request, **page_data}
        )
    except ChatSessionNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/turns/{turn_id}/cancel", response_class=HTMLResponse)
@htmx("chat/partials/cancel_turn_response")
async def cancel_turn(
    request: Request,
    turn_id: str,
    registry: ActiveRunRegistry = Depends(get_active_run_registry),
):
    original_message = await registry.cancel(turn_id=turn_id)

    return {
        "content": original_message,
        "turn_id": turn_id,
    }


@router.websocket("/ws/session/{session_id}", name="conversation_websocket")
async def conversation_websocket(
    websocket: WebSocket,
    session_id: int,
    coder_service: CoderService = Depends(get_coder_service),
):
    ws_manager = WebSocketConnectionManager(websocket)
    await ws_manager.connect()
    orchestrator = WebSocketOrchestrator(
        ws_manager=ws_manager, session_id=session_id, coder_service=coder_service
    )
    await orchestrator.handle_connection()
