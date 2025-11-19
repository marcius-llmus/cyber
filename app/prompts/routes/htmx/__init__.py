from fastapi import APIRouter

from app.prompts.routes.htmx.blueprints import router as blueprint_router
from app.prompts.routes.htmx.commons import router as common_router
from app.prompts.routes.htmx.globals import router as global_router
from app.prompts.routes.htmx.projects import router as project_router

router = APIRouter()
router.include_router(global_router)
router.include_router(project_router)
router.include_router(blueprint_router)
router.include_router(common_router)