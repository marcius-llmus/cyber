class HistoryException(Exception):
    """Base exception for history application."""


class ChatSessionNotFoundException(HistoryException):
    """Raised when a chat session is not found."""