"""Custom exceptions for the AI Agent service."""

from typing import Any


class AIAgentException(Exception):
    """Base exception for all AI Agent errors.

    This base class provides common error handling attributes that can be
    converted to Problem Details format without exposing service internals.
    """

    def __init__(
        self,
        message: str,
        problem_type: str,
        title: str,
        status_code: int = 500,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error detail
            problem_type: Problem type identifier (e.g., 'validation-error')
            title: Short human-readable summary
            status_code: HTTP status code
        """
        super().__init__(message)
        self.message = message
        self.problem_type = problem_type
        self.title = title
        self.status_code = status_code


class ValidationError(AIAgentException):
    """Raised when request validation fails."""

    def __init__(self, message: str) -> None:
        """Initialize validation error.

        Args:
            message: Detailed validation error message
        """
        super().__init__(
            message=message,
            problem_type="validation-error",
            title="Validation Error",
            status_code=400,
        )


class TemplateGenerationError(AIAgentException):
    """Raised when template generation fails."""

    def __init__(self, message: str = "Failed to generate template") -> None:
        """Initialize template generation error.

        Args:
            message: Detailed error message
        """
        super().__init__(
            message=message,
            problem_type="generation-error",
            title="Template Generation Error",
            status_code=500,
        )


class LLMProviderError(AIAgentException):
    """Raised when LLM provider communication fails."""

    def __init__(self, message: str = "LLM provider communication failed") -> None:
        """Initialize LLM provider error.

        Args:
            message: Detailed error message
        """
        super().__init__(
            message=message,
            problem_type="llm-provider-error",
            title="LLM Provider Error",
            status_code=502,
        )


class TemplateParsingError(AIAgentException):
    """Raised when template parsing fails."""

    def __init__(self, message: str = "Failed to parse template response") -> None:
        """Initialize template parsing error.

        Args:
            message: Detailed error message
        """
        super().__init__(
            message=message,
            problem_type="parsing-error",
            title="Template Parsing Error",
            status_code=500,
        )


class ConfigurationError(AIAgentException):
    """Raised when service configuration is invalid."""

    def __init__(self, message: str) -> None:
        """Initialize configuration error.

        Args:
            message: Detailed error message
        """
        super().__init__(
            message=message,
            problem_type="configuration-error",
            title="Configuration Error",
            status_code=500,
        )
