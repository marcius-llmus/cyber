class UsageException(Exception):
    """Base exception for usage application."""


class UsageTrackingException(UsageException):
    """Raised when an event cannot be tracked or calculated."""