"""Custom exceptions for the AI Agent API.

This module defines custom exception classes that are used throughout
the application and are handled by the exception handlers to produce
RFC 7807 Problem Details responses.
"""

from typing import Any


class AIAgentException(Exception):
    """Base exception for all AI Agent errors.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code for this error
        error_type: URI identifying the error type
        errors: Additional error details
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_type: str | None = None,
        errors: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code (default: 500)
            error_type: URI identifying the error type (default: generated from class name)
            errors: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type or self._generate_error_type()
        self.errors = errors

    def _generate_error_type(self) -> str:
        """Generate error type URI from class name."""
        import re

        # Convert CamelCase to kebab-case
        name = self.__class__.__name__
        if name.endswith("Error"):
            name = name[:-5]  # Remove "Error" suffix

        # Convert to kebab-case (handle consecutive uppercase letters)
        # First, handle transitions from lowercase to uppercase
        kebab_name = re.sub(r"([a-z\d])([A-Z])", r"\1-\2", name)
        # Then handle transitions from multiple uppercase to lowercase
        kebab_name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", kebab_name)
        # Convert to lowercase
        kebab_name = kebab_name.lower()

        return f"https://api.dilcore.ai/errors/{kebab_name}"

    @property
    def title(self) -> str:
        """Get the error title from the class name."""
        name = self.__class__.__name__
        if name.endswith("Error"):
            name = name[:-5]

        # Convert CamelCase to Title Case with spaces
        title_parts = []
        current_word = []

        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                if current_word:
                    title_parts.append("".join(current_word))
                current_word = [char]
            else:
                current_word.append(char)

        if current_word:
            title_parts.append("".join(current_word))

        return " ".join(title_parts)


class ValidationError(AIAgentException):
    """Exception raised for request validation errors."""

    def __init__(
        self,
        message: str = "Request validation failed",
        errors: dict[str, Any] | None = None,
    ) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            errors: Validation error details
        """
        super().__init__(
            message=message,
            status_code=422,
            error_type="https://api.dilcore.ai/errors/validation-error",
            errors=errors,
        )

    @property
    def title(self) -> str:
        """Get the error title."""
        return "Validation Error"


class TemplateGenerationError(AIAgentException):
    """Exception raised when template generation fails."""

    def __init__(
        self,
        message: str = "Template generation failed",
        errors: dict[str, Any] | None = None,
    ) -> None:
        """Initialize template generation error.

        Args:
            message: Error message
            errors: Additional error details
        """
        super().__init__(
            message=message,
            status_code=500,
            errors=errors,
        )


class LLMAPIError(AIAgentException):
    """Exception raised when LLM API calls fail."""

    def __init__(
        self,
        message: str = "LLM API call failed",
        errors: dict[str, Any] | None = None,
    ) -> None:
        """Initialize LLM API error.

        Args:
            message: Error message
            errors: Additional error details
        """
        super().__init__(
            message=message,
            status_code=502,
            error_type="https://api.dilcore.ai/errors/llm-api",
            errors=errors,
        )

    @property
    def title(self) -> str:
        """Get the error title."""
        return "LLM API"


class ParsingError(AIAgentException):
    """Exception raised when parsing LLM response fails."""

    def __init__(
        self,
        message: str = "Failed to parse LLM response",
        errors: dict[str, Any] | None = None,
    ) -> None:
        """Initialize parsing error.

        Args:
            message: Error message
            errors: Additional error details
        """
        super().__init__(
            message=message,
            status_code=500,
            errors=errors,
        )


class ConfigurationError(AIAgentException):
    """Exception raised for configuration errors."""

    def __init__(
        self,
        message: str = "Configuration error",
        errors: dict[str, Any] | None = None,
    ) -> None:
        """Initialize configuration error.

        Args:
            message: Error message
            errors: Additional error details
        """
        super().__init__(
            message=message,
            status_code=500,
            errors=errors,
        )
