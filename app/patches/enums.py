from enum import StrEnum


class DiffPatchStatus(StrEnum):
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"
    FAILED = "failed"


class PatchStrategy(StrEnum):
    LLM_GATHER = "llm_gather"
    PROGRAMMATIC = "programmatic"
