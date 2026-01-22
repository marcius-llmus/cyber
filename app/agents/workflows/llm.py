from typing import Dict, Any

from pydantic import BaseModel, Field, field_validator, ValidationError


class ToolSelection(BaseModel):
    """Tool selection."""

    tool_id: str = Field(description="Tool ID to select.")
    tool_name: str = Field(description="Tool name to select.")
    tool_kwargs: Dict[str, Any] = Field(description="Keyword arguments for the tool.")

    @field_validator("tool_kwargs", mode="wrap") # noqa
    @classmethod
    def ignore_non_dict_arguments(cls, v: Any, handler: Any) -> Dict[str, Any]:
        try:
            return handler(v)
        except ValidationError:
            return handler({})
