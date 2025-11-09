from enum import StrEnum


class CoderEventType(StrEnum):
    USER_MESSAGE = "user_message"
    AI_MESSAGE_CHUNK = "ai_message_chunk"
    AI_MESSAGE_COMPLETED = "ai_message_completed"
    CODE_DIFF_CHUNK = "code_diff_chunk"
    CONTEXT_FILE_ADDED = "context_file_added"
    USAGE_METRICS_UPDATED = "usage_metrics_updated"
    SYSTEM_LOG_APPENDED = "system_log_append"
    ERROR = "error"
