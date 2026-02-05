import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.chat.routes.htmx import router as chat_htmx_router
from app.coder.factories import build_turn_execution_registry
from app.coder.routes.htmx import router as coder_htmx_router
from app.coder.services.execution_registry import initialize_global_registry
from app.commons.fastapi_htmx import htmx_init
from app.context.routes.htmx import router as context_htmx_router
from app.core.config import settings
from app.core.db import sessionmanager
from app.core.observability import init_observability
from app.core.setup import initialize_workspace
from app.core.templating import templates
from app.projects.routes.htmx import router as projects_htmx_router
from app.prompts.routes.htmx import router as prompts_htmx_router
from app.sessions.routes.htmx import router as sessions_htmx_router
from app.settings.routes.htmx import router as settings_htmx_router
from app.settings.utils import initialize_application_settings
from app.usage.factories import build_price_updater

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa
    """
    Ensures that the default application settings are created on startup.
    Also ensures that the workspace directories exist and are seeded.
    """
    initialize_workspace()

    # Initialize global in-memory turn execution handler registries
    registry = build_turn_execution_registry()
    initialize_global_registry(registry)

    price_updater = build_price_updater()
    # Start the background price updater (wait=False to avoid blocking startup)
    price_updater.start(wait=False)

    # Initialize Observability (Arize Phoenix) if enabled
    if settings.OBSERVABILITY_ENABLED:
        init_observability()

    async with sessionmanager.session() as session:
        await initialize_application_settings(session)

    yield

    price_updater.stop()
    await sessionmanager.cleanup()


app = FastAPI(lifespan=lifespan)

htmx_init(templates=templates, file_extension="html")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(coder_htmx_router, prefix="/coder", tags=["coder"])
app.include_router(settings_htmx_router, prefix="/settings", tags=["settings"])
app.include_router(projects_htmx_router, prefix="/projects", tags=["projects"])
app.include_router(prompts_htmx_router, prefix="/prompts", tags=["prompts"])
app.include_router(context_htmx_router, prefix="/context", tags=["context"])
app.include_router(sessions_htmx_router, prefix="/sessions", tags=["sessions"])
app.include_router(chat_htmx_router, prefix="/chat", tags=["chat"])


@app.get("/")
async def root():
    return RedirectResponse(url="/coder")
