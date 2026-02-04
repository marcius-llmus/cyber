from app.chat.schemas import Turn
from app.coder.services.messaging import MessagingTurnEventHandler
from app.coder.services.single_shot_patching import SingleShotPatchService
from app.coder.services.execution_registry import TurnExecutionRegistry
from app.context.factories import build_workspace_service
from app.core.db import sessionmanager
from app.patches.factories import build_diff_patch_service


async def build_messaging_turn_event_handler(
    *, turn: Turn
) -> MessagingTurnEventHandler:
    return MessagingTurnEventHandler(turn=turn)


async def build_single_shot_patch_service() -> SingleShotPatchService:
    return SingleShotPatchService(
        db=sessionmanager,
        diff_patch_service_factory=build_diff_patch_service,
        context_service_factory=build_workspace_service,
    )


def build_turn_execution_registry() -> TurnExecutionRegistry:
    return TurnExecutionRegistry()
