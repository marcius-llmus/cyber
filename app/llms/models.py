from sqlalchemy import Column, Enum, Integer, String, UniqueConstraint, JSON

from app.core.db import Base
from app.llms.enums import LLMProvider, LLMRole


class LLMSettings(Base):
    __tablename__ = "llm_settings"

    id = Column(Integer, primary_key=True)
    model_name = Column(String, nullable=False, unique=True)
    provider = Column(Enum(LLMProvider), nullable=False)
    # todo: we should move this to provider later so we don't need to mass update keys
    api_key = Column(String, nullable=True)
    context_window = Column(Integer, nullable=False)
    active_role = Column(Enum(LLMRole), nullable=True, unique=True)
    reasoning_config = Column(JSON, nullable=True)

    __table_args__ = (UniqueConstraint("model_name", name="_model_name_uc"),)
