from enum import StrEnum


class LogLevel(StrEnum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class ContextStrategy(StrEnum):
    MANUAL = "MANUAL"
    GREP = "GREP"
    RAG = "RAG"
    GREP_RAG = "GREP_RAG"


class OperationalMode(StrEnum):
    CODING = "CODING"
    ASK = "ASK"
    CHAT = "CHAT"
    PLANNER = "PLANNER"
    SINGLE_SHOT = "SINGLE_SHOT"


class RepoMapMode(StrEnum):
    AUTO = "AUTO"
    TREE = "TREE"
    MANUAL = "MANUAL"
