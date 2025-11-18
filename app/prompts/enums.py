from enum import StrEnum


class PromptType(StrEnum):
    SYSTEM = "system"
    GLOBAL = "global"
    PROJECT = "project"
    BLUEPRINT = "blueprint"


class PromptEventType(StrEnum):
    BLUEPRINTS_CHANGED = "refreshBlueprints"
