"""Problem Details schema models based on RFC 7807.

This module defines the Problem Details response format for API errors,
following the RFC 7807 standard for HTTP API error responses.
"""

from typing import Any

from pydantic import BaseModel, Field


class ProblemDetails(BaseModel):
    """Problem Details response model based on RFC 7807.

    This model provides a standardized format for API error responses,
    making it easier for clients to understand and handle errors consistently.

    Attributes:
        type: A URI reference that identifies the problem type
        title: A short, human-readable summary of the problem type
        status: The HTTP status code
        detail: A human-readable explanation specific to this occurrence
        instance: A URI reference that identifies the specific occurrence
        errors: Optional additional error details (e.g., validation errors)
    """

    type: str = Field(
        ...,
        description="A URI reference that identifies the problem type",
        examples=["https://api.example.com/errors/validation-error"],
    )
    title: str = Field(
        ...,
        description="A short, human-readable summary of the problem type",
        examples=["Validation Error"],
    )
    status: int = Field(
        ...,
        description="The HTTP status code",
        ge=100,
        le=599,
        examples=[400],
    )
    detail: str = Field(
        ...,
        description="A human-readable explanation specific to this occurrence",
        examples=["The prompt field must not be empty"],
    )
    instance: str | None = Field(
        None,
        description="A URI reference that identifies the specific occurrence",
        examples=["/api/v1/metadata/generate"],
    )
    errors: dict[str, Any] | None = Field(
        None,
        description="Additional error details (e.g., validation errors)",
        examples=[{"prompt": ["Field required"]}],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "https://api.example.com/errors/validation-error",
                "title": "Validation Error",
                "status": 422,
                "detail": "Request validation failed",
                "instance": "/api/v1/metadata/generate",
                "errors": {
                    "prompt": ["Field required"],
                },
            }
        }
    }
