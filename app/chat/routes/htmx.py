from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.post("/clear", response_class=PlainTextResponse)
async def clear_chat(request: Request):  # noqa
    # This will later clear the session history and return the initial state
    # For now, it returns an empty response as the list is cleared on the frontend.
    return ""