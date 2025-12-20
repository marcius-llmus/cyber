from app.blueprints.services import BlueprintService
from app.context.factories import build_codebase_service


async def get_blueprint_service() -> BlueprintService:
    codebase_service = await build_codebase_service()
    return BlueprintService(codebase_service=codebase_service)
