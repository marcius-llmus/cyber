from enum import StrEnum


class MessageRole(StrEnum):
    USER = "USER"
    AI = "AI"
    SYSTEM = "SYSTEM"