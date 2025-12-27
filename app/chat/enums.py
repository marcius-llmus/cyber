from enum import StrEnum


class MessageRole(StrEnum):
    USER = "user"
    AI = "assistant"
    SYSTEM = "system"


class PatchStatus(StrEnum):
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"
    FAILED = "failed"
