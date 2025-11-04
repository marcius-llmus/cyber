from typing import NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict

from app.projects.models import Project
from app.blueprints.schemas import Blueprint
from app.prompts.enums import PromptType
from app.prompts.models import Prompt


class PromptBase(BaseModel):
    name: str
    content: str


class PromptCreate(PromptBase):
    pass


class PromptInternalCreate(PromptBase):
    type: PromptType
    source_path: str | None = None
    project_id: int | None = None


class PromptUpdate(PromptBase):
    name: str | None = None
    content: str | None = None
    source_path: str | None = None


class PromptRead(PromptBase):
    id: int
    project_id: int | None = None
    model_config = ConfigDict(from_attributes=True)


class PromptsPageContext(TypedDict):
    global_prompts: list[Prompt]
    project_prompts: list[Prompt]
    active_project: Project | None
    blueprint_prompt: Prompt | None
    blueprints: list[Blueprint]
    attached_prompt_ids: set[int]


class BlueprintRequest(BaseModel):
    path: str