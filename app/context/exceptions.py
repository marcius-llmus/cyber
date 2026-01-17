class ContextException(Exception):
    """Base exception for context application."""


class RepoMapExtractionException(ContextException):
    """Raised when extracting tags from a file fails."""
