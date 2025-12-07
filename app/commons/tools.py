from llama_index.core.tools.tool_spec.base import BaseToolSpec
from app.core.db import DatabaseSessionManager
from app.settings.models import Settings


class BaseToolSet(BaseToolSpec):
    """
    Base Class for a set of Agent Tools, inheriting from LlamaIndex BaseToolSpec.
    Enforces standardized initialization with DB and Settings.
    """
    def __init__(
        self,
        db: DatabaseSessionManager,
        settings: Settings,
        session_id: int | None = None,
    ):
        super().__init__()
        self.db = db
        self.settings = settings
        self.session_id = session_id
