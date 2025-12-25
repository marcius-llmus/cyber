from enum import StrEnum


class OperationalMode(StrEnum):
    CODING = "coding"
    ASK = "ask"
    CHAT = "chat"
    PLANNER = "planner"
    SINGLE_SHOT = "single_shot"


class CodingMode(StrEnum):
    AGENT = "agent"
    SINGLE_SHOT = "single_shot"


class ContextStrategy(StrEnum):
    MANUAL = "manual"
    AUTO_GATHER = "auto_gather"
    RAG = "rag"
