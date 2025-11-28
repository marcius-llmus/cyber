import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.commons.fastapi_htmx import htmx_init

from app.core.db import sessionmanager
from app.coder.routes.htmx import router as coder_htmx_router
from app.chat.routes.htmx import router as chat_htmx_router
from app.core.templating import templates
from app.projects.routes.htmx import router as projects_htmx_router
from app.context.routes.htmx import router as context_htmx_router
from app.history.routes.htmx import router as history_htmx_router
from app.prompts.routes.htmx import router as prompts_htmx_router
from app.settings.routes.htmx import router as settings_htmx_router
from app.settings.utils import initialize_application_settings
from app.core.config import settings
from app.core.observability import init_observability


logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI): # noqa
    """
    Ensures that the default application settings are created on startup.
    """
    # Initialize Observability (Arize Phoenix) if enabled
    if settings.OBSERVABILITY_ENABLED:
        init_observability()

    async with sessionmanager.session() as session:
        await initialize_application_settings(session)
    yield
    await sessionmanager.cleanup()


app = FastAPI(lifespan=lifespan)

htmx_init(templates=templates, file_extension="html")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(coder_htmx_router, prefix="/coder", tags=["coder"])
app.include_router(settings_htmx_router, prefix="/settings", tags=["settings"])
app.include_router(projects_htmx_router, prefix="/projects", tags=["projects"])
app.include_router(prompts_htmx_router, prefix="/prompts", tags=["prompts"])
app.include_router(context_htmx_router, prefix="/context", tags=["context"])
app.include_router(history_htmx_router, prefix="/history", tags=["history"])
app.include_router(chat_htmx_router, prefix="/chat", tags=["chat"])


@app.get("/")
async def root():
    return RedirectResponse(url="/coder")