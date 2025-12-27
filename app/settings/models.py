from sqlalchemy import (
    Column,
    Boolean,
    Enum,
    Float,
    Integer
)

from app.core.db import Base
from app.core.enums import CodingMode, ContextStrategy, OperationalMode


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, default=1)
    operational_mode = Column(Enum(OperationalMode, name="operationalmode"), nullable=False)
    coding_mode = Column(Enum(CodingMode, name="codingmode"), nullable=False)
    context_strategy = Column(Enum(ContextStrategy, name="contextstrategy"), nullable=False)
    max_history_length = Column(Integer, nullable=False)
    coding_llm_temperature = Column(Float, nullable=False) # todo: shall be in llm models later
    ast_token_limit = Column(Integer, nullable=False)
    grep_token_limit = Column(Integer, nullable=False, default=4000)
    diff_patches_auto_open = Column(Boolean, nullable=False, default=True, server_default="t")
    diff_patches_auto_apply = Column(Boolean, nullable=False, default=False, server_default="f")