"""API routes for the AI Agent API.

This module defines the API endpoints and demonstrates
problem details error handling.
"""

import hashlib
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ai_agent.exceptions import (
    LLMAPIError,
    ParsingError,
    TemplateGenerationError,
    ValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["API"])


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Application status")
    version: str = Field(..., description="Application version")


class GenerateRequest(BaseModel):
    """Request model for template generation."""

    prompt: str = Field(
        ...,
        description="The prompt for template generation",
        min_length=1,
        max_length=4000,
    )
    options: dict[str, Any] | None = Field(
        None,
        description="Optional generation options",
    )


class GenerateResponse(BaseModel):
    """Response model for template generation."""

    template: str = Field(..., description="Generated template")
    metadata: dict[str, Any] = Field(..., description="Generation metadata")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        Application health status and version
    """
    return HealthResponse(
        status="healthy",
        version="0.1.0",
    )


@router.post("/generate", response_model=GenerateResponse)
async def generate_template(request: GenerateRequest) -> GenerateResponse:
    """Generate a template from a prompt.

    This endpoint demonstrates various error handling scenarios:
    - Validation errors (handled by FastAPI automatically)
    - Custom business logic errors (using custom exceptions)
    - LLM API errors
    - Parsing errors

    Args:
        request: Template generation request

    Returns:
        Generated template and metadata

    Raises:
        ValidationError: If the request is invalid
        TemplateGenerationError: If template generation fails
        LLMAPIError: If LLM API call fails
        ParsingError: If response parsing fails
    """
    prompt_hash = hashlib.sha256(request.prompt.encode()).hexdigest()
    logger.info(
        "Generating template for prompt (len=%d, sha256=%s)",
        len(request.prompt),
        prompt_hash,
    )

    # Simulate validation error for demonstration
    if "error" in request.prompt.lower():
        if "validation" in request.prompt.lower():
            raise ValidationError(
                message="Invalid prompt content",
                errors={"prompt": ["Prompt cannot contain 'validation error'"]},
            )
        elif "llm" in request.prompt.lower():
            raise LLMAPIError(
                message="Failed to connect to LLM API",
                errors={"provider": "OpenRouter", "status": "unavailable"},
            )
        elif "parsing" in request.prompt.lower():
            raise ParsingError(
                message="Failed to parse LLM response",
                errors={"expected": "JSON", "received": "text"},
            )
        elif "template" in request.prompt.lower():
            raise TemplateGenerationError(
                message="Template generation failed due to invalid constraints",
                errors={"constraint": "max_length", "value": 10000},
            )
        elif "http" in request.prompt.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable",
            )
        elif "unhandled" in request.prompt.lower():
            # Simulate an unhandled exception
            raise RuntimeError("This is an unhandled exception for testing")

    # Simulate successful template generation
    template = f"Generated template for: {request.prompt}"
    metadata = {
        "prompt_length": len(request.prompt),
        "template_length": len(template),
        "model": "example-model",
        "timestamp": "2026-01-17T00:00:00Z",
    }

    return GenerateResponse(template=template, metadata=metadata)


@router.get("/error/{error_type}")
async def trigger_error(error_type: str) -> dict[str, str]:
    """Trigger different types of errors for testing.

    This endpoint is useful for testing the problem details error handling.

    Args:
        error_type: Type of error to trigger (validation, llm, parsing, template, http, unhandled)

    Returns:
        Success message (never reached)

    Raises:
        Various exceptions based on error_type parameter
    """
    if error_type == "validation":
        raise ValidationError(
            message="Validation failed",
            errors={"field": ["Invalid value"]},
        )
    elif error_type == "llm":
        raise LLMAPIError(
            message="LLM API error",
            errors={"api": "connection_failed"},
        )
    elif error_type == "parsing":
        raise ParsingError(
            message="Parsing error",
            errors={"line": 42},
        )
    elif error_type == "template":
        raise TemplateGenerationError(
            message="Template generation error",
            errors={"reason": "invalid_format"},
        )
    elif error_type == "http":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )
    elif error_type == "unhandled":
        raise RuntimeError("Unhandled runtime error")
    else:
        return {"message": f"No error triggered for type: {error_type}"}
