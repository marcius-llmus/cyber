from sqlalchemy import (
    Column,
    Boolean,
    Float,
    Integer
)

from app.core.db import Base


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, default=1)
    max_history_length = Column(Integer, nullable=False)
    coding_llm_temperature = Column(Float, nullable=False) # todo: shall be in llm models later
    ast_token_limit = Column(Integer, nullable=False)
    grep_token_limit = Column(Integer, nullable=False, default=4000)
    diff_patches_auto_open = Column(Boolean, nullable=False, default=True, server_default="t")
    diff_patches_auto_apply = Column(Boolean, nullable=False, default=False, server_default="f")