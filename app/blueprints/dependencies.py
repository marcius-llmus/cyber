from app.blueprints.services import BlueprintService


async def get_blueprint_service() -> BlueprintService:
    return BlueprintService()