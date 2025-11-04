from enum import StrEnum


class PromptType(StrEnum):
    SYSTEM = "system"
    GLOBAL = "global"
    PROJECT = "project"
    BLUEPRINT = "blueprint"


class PromptEventType(StrEnum):
    GLOBAL_PROMPTS_CHANGED = "globalPromptsChanged"
    PROJECT_PROMPTS_CHANGED = "projectPromptsChanged"
    BLUEPRINTS_CHANGED = "refreshBlueprints"