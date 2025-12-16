from sqlalchemy.ext.asyncio import AsyncSession

from app.coder.patcher import PatcherService
from app.coder.services import TurnEventHandler
from app.llms.factories import build_llm_service
from app.context.factories import build_codebase_service
from app.projects.factories import build_project_service
from app.chat.factories import build_message_accumulator


async def build_patcher_service(db: AsyncSession) -> PatcherService:
    llm_service = await build_llm_service(db)
    project_service = await build_project_service(db)
    codebase_service = await build_codebase_service()
    return PatcherService(
        llm_service=llm_service,
        project_service=project_service,
        codebase_service=codebase_service,
    )


def build_turn_event_handler() -> TurnEventHandler:
    accumulator = build_message_accumulator()
    return TurnEventHandler(accumulator=accumulator)
