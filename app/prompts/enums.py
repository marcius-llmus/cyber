from enum import StrEnum


class PromptType(StrEnum):
    SYSTEM = "SYSTEM"
    GLOBAL = "GLOBAL"
    PROJECT = "PROJECT"
    BLUEPRINT = "BLUEPRINT"


class PromptEventType(StrEnum):
    BLUEPRINTS_CHANGED = "refreshBlueprints"
