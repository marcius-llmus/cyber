from pydantic import BaseModel
from pydantic import Field
from app.llms.enums import LLMModel, LLMProvider


class LLM(BaseModel):
    model_name: LLMModel
    provider: LLMProvider
    default_context_window: int = Field(gt=0)
