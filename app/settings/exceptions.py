class SettingsException(Exception):
    """Base exception for settings application."""


class SettingsNotFoundException(SettingsException):
    """Raised when application settings are not found."""


class LLMSettingsNotFoundException(SettingsException):
    """Raised when LLM settings are not found."""


class LLMSettingsAlreadyExistsException(SettingsException):
    """Raised when trying to create LLM settings that already exist."""


class ContextWindowExceededException(SettingsException):
    """Raised when the user-configured context window exceeds the model's maximum."""