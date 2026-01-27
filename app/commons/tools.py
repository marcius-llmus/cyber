from app.agents.tools.tool_spec import CustomBaseToolSpec
from app.core.db import DatabaseSessionManager
from app.settings.schemas import AgentSettingsSnapshot


class BaseToolSet(CustomBaseToolSpec):
    """
    Base Class for a set of Agent Tools, inheriting from LlamaIndex BaseToolSpec.
    Enforces standardized initialization with DB and Settings.
    """

    def __init__(
        self,
        db: DatabaseSessionManager,
        settings_snapshot: AgentSettingsSnapshot,
        session_id: int | None = None,
        turn_id: str | None = None,
    ):
        self.db = db
        self.settings_snapshot = settings_snapshot
        self.session_id = session_id
        self.turn_id = turn_id
