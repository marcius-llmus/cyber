from enum import StrEnum


class LogLevel(StrEnum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class CodingMode(StrEnum):
    AGENT = "AGENT"
    SINGLE_SHOT = "SINGLE_SHOT"


class ContextStrategy(StrEnum):
    MANUAL = "MANUAL"
    AUTO_GATHER = "AUTO_GATHER"
    RAG = "RAG"


class OperationalMode(StrEnum):
    CODING = "CODING"
    ASK = "ASK"
    CHAT = "CHAT"
    PLANNER = "PLANNER"
    SINGLE_SHOT = "SINGLE_SHOT"
