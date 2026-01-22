from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator


class ToolSelection(BaseModel):
    """Tool selection."""

    tool_id: str = Field(description="Tool ID to select.")
    tool_name: str = Field(description="Tool name to select.")
    tool_kwargs: dict[str, Any] = Field(description="Keyword arguments for the tool.")

    @field_validator("tool_kwargs", mode="wrap")  # noqa
    @classmethod
    def ignore_non_dict_arguments(cls, v: Any, handler: Any) -> dict[str, Any]:
        try:
            return handler(v)
        except ValidationError:
            return handler({})
