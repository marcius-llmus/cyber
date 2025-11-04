from enum import StrEnum


class PromptType(StrEnum):
    SYSTEM = "system"
    GLOBAL = "global"
    PROJECT = "project"
    BLUEPRINT = "blueprint"