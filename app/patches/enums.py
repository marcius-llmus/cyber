from enum import StrEnum


class DiffPatchStatus(StrEnum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class PatchProcessorType(StrEnum):
    """How a stored patch text should be interpreted/applied."""

    UDIFF_LLM = "UDIFF_LLM"
    CODEX_APPLY = "CODEX_APPLY"


class ParsedPatchOperation(StrEnum):
    ADD = "ADD"
    MODIFY = "MODIFY"
    DELETE = "DELETE"
    RENAME = "RENAME"
