from abc import ABC, abstractmethod
from typing import List

from llama_index.core.tools import FunctionTool
from app.core.db import DatabaseSessionManager
from app.settings.models import Settings


class BaseToolSet(ABC):
    """
    Abstract Base Class for a set of Agent Tools.
    Enforces standardized initialization with DB and Settings.
    """
    def __init__(
        self,
        db: DatabaseSessionManager,
        settings: Settings,
        session_id: int | None = None,
    ):
        self.db = db
        self.settings = settings
        self.session_id = session_id

    @property
    @abstractmethod
    def slug(self) -> str:
        """Unique identifier for this tool set (used for settings/toggles)."""

    @abstractmethod
    def get_tools(self) -> List[FunctionTool]:
        """Returns the list of LlamaIndex FunctionTools for this set."""