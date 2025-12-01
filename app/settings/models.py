from sqlalchemy import (
    Column,
    Enum,
    Float,
    Integer
)

from app.core.db import Base
from app.settings.enums import CodingMode, ContextStrategy, OperationalMode


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, default=1)
    operational_mode = Column(Enum(OperationalMode), nullable=False)
    coding_mode = Column(Enum(CodingMode), nullable=False)
    context_strategy = Column(Enum(ContextStrategy), nullable=False)
    max_history_length = Column(Integer, nullable=False)
    coding_llm_temperature = Column(Float, nullable=False)
    ast_token_limit = Column(Integer, nullable=False)
