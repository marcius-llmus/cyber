class HistoryException(Exception):
    """Base exception for sessions application."""


class ChatSessionNotFoundException(HistoryException):
    """Raised when a chat session is not found."""
