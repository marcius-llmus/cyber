import uuid

from app.chat.enums import ChatTurnStatus
from app.chat.repositories import ChatTurnRepository
from app.chat.schemas import ChatTurnCreate, ChatTurnUpdate


class ChatTurnService:
    def __init__(self, turn_repo: ChatTurnRepository):
        self.turn_repo = turn_repo

    async def start_turn(self, *, session_id: int, turn_id: str | None = None) -> str:
        if turn_id is None:
            new_turn_id = str(uuid.uuid4())
            await self.turn_repo.create(
                obj_in=ChatTurnCreate(
                    id=new_turn_id, session_id=session_id, status=ChatTurnStatus.PENDING
                )
            )
            return new_turn_id

        existing = await self.turn_repo.get_by_id_and_session(
            turn_id=turn_id, session_id=session_id
        )
        if not existing:
            raise ValueError(
                f"Retry requested for turn {turn_id}, but it does not exist"
            )

        if existing.status == ChatTurnStatus.SUCCEEDED:
            raise ValueError(f"Turn {turn_id} already succeeded and cannot be retried")

        return turn_id

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
