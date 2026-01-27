import uuid

from app.chat.enums import ChatTurnStatus
from app.chat.repositories import ChatTurnRepository
from app.chat.schemas import ChatTurnCreate, ChatTurnUpdate, Turn
from app.settings.schemas import AgentSettingsSnapshot
from app.settings.services import SettingsService


class ChatTurnService:
    def __init__(
        self, turn_repo: ChatTurnRepository, settings_service: SettingsService
    ):
        self.turn_repo = turn_repo
        self.settings_service = settings_service

    async def start_turn(
        self, *, session_id: int, retry_turn_id: str | None = None
    ) -> Turn:
        settings_snapshot = await self.generate_settings_snapshot()

        if retry_turn_id is None:
            new_turn_id = str(uuid.uuid4())
            await self.turn_repo.create(
                obj_in=ChatTurnCreate(
                    id=new_turn_id, session_id=session_id, status=ChatTurnStatus.PENDING
                )
            )
            return Turn(turn_id=new_turn_id, settings_snapshot=settings_snapshot)

        existing = await self.turn_repo.get_by_id_and_session(
            turn_id=retry_turn_id, session_id=session_id
        )
        if not existing:
            raise ValueError(
                f"Retry requested for turn {retry_turn_id}, but it does not exist"
            )

        if existing.status == ChatTurnStatus.SUCCEEDED:
            raise ValueError(
                f"Turn {retry_turn_id} already succeeded and cannot be retried"
            )

        return Turn(turn_id=retry_turn_id, settings_snapshot=settings_snapshot)

    async def generate_settings_snapshot(self) -> AgentSettingsSnapshot:
        settings = await self.settings_service.get_settings()
        return AgentSettingsSnapshot.model_validate(settings)

    async def mark_succeeded(self, *, session_id: int, turn_id: str) -> None:
        turn = await self.turn_repo.get_by_id_and_session(
            turn_id=turn_id, session_id=session_id
        )
        if not turn:
            raise ValueError(f"Turn {turn_id} not found")
        await self.turn_repo.update(
            db_obj=turn,
            obj_in=ChatTurnUpdate(status=ChatTurnStatus.SUCCEEDED),
        )
