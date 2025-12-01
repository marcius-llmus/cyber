from sqlalchemy import Column, Enum, Integer, String, UniqueConstraint
from app.core.db import Base
from app.llms.enums import LLMProvider


class LLMSettings(Base):
    __tablename__ = "llm_settings"

    id = Column(Integer, primary_key=True)
    model_name = Column(String, nullable=False, unique=True)
    provider = Column(Enum(LLMProvider), nullable=False)
    api_key = Column(String, nullable=True)
    context_window = Column(Integer, nullable=False)

    __table_args__ = (UniqueConstraint("model_name", name="_model_name_uc"),)
