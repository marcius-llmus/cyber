from enum import StrEnum


class PromptType(StrEnum):
    SYSTEM = "system"
    GLOBAL = "global"
    PROJECT = "project"
    BLUEPRINT = "blueprint"


class PromptTargetSelector(StrEnum):
    GLOBAL = "#global-prompt-list-container"
    PROJECT = "#project-prompt-list-container"
