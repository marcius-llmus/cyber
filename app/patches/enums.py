from enum import StrEnum


class DiffPatchStatus(StrEnum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class PatchStrategy(StrEnum):
    LLM_GATHER = "LLM_GATHER"
    PROGRAMMATIC = "PROGRAMMATIC"
