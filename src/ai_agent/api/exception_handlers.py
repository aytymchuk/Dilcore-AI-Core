"""Exception handlers for the AI Agent API.

This module defines exception handlers that convert exceptions into
RFC 7807 Problem Details responses.
"""

import logging
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from ai_agent.exceptions import AIAgentException
from ai_agent.schemas.problem_details import ProblemDetails

logger = logging.getLogger(__name__)


def ai_agent_exception_handler(
    request: Request, exc: AIAgentException
) -> JSONResponse:
    """Handle custom AI Agent exceptions.

    Args:
        request: The incoming request
        exc: The AI Agent exception

    Returns:
        JSONResponse with Problem Details format
    """
    logger.error(
        "AI Agent exception: %s",
        exc.message,
        exc_info=True,
        extra={
            "error_type": exc.error_type,
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )

    problem = ProblemDetails(
        type=exc.error_type,
        title=exc.title,
        status=exc.status_code,
        detail=exc.message,
        instance=request.url.path,
        errors=exc.errors,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )


def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions.

    Args:
        request: The incoming request
        exc: The HTTP exception

    Returns:
        JSONResponse with Problem Details format
    """
    logger.warning(
        "HTTP exception: %s - %s",
        exc.status_code,
        exc.detail,
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )

    # Map status codes to error types and titles
    error_mapping = {
        status.HTTP_400_BAD_REQUEST: ("bad-request", "Bad Request"),
        status.HTTP_401_UNAUTHORIZED: ("unauthorized", "Unauthorized"),
        status.HTTP_403_FORBIDDEN: ("forbidden", "Forbidden"),
        status.HTTP_404_NOT_FOUND: ("not-found", "Not Found"),
        status.HTTP_405_METHOD_NOT_ALLOWED: ("method-not-allowed", "Method Not Allowed"),
        status.HTTP_409_CONFLICT: ("conflict", "Conflict"),
        status.HTTP_422_UNPROCESSABLE_ENTITY: (
            "validation-error",
            "Validation Error",
        ),
        status.HTTP_429_TOO_MANY_REQUESTS: ("too-many-requests", "Too Many Requests"),
        status.HTTP_500_INTERNAL_SERVER_ERROR: (
            "internal-server-error",
            "Internal Server Error",
        ),
        status.HTTP_502_BAD_GATEWAY: ("bad-gateway", "Bad Gateway"),
        status.HTTP_503_SERVICE_UNAVAILABLE: (
            "service-unavailable",
            "Service Unavailable",
        ),
    }

    error_type_slug, error_title = error_mapping.get(
        exc.status_code, ("http-error", "HTTP Error")
    )

    problem = ProblemDetails(
        type=f"https://api.dilcore.ai/errors/{error_type_slug}",
        title=error_title,
        status=exc.status_code,
        detail=str(exc.detail),
        instance=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )


def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI request validation errors.

    Args:
        request: The incoming request
        exc: The validation exception

    Returns:
        JSONResponse with Problem Details format
    """
    validation_errors = exc.errors()
    # Log error count without exposing user input
    logger.warning(
        "Validation error occurred",
        extra={
            "path": request.url.path,
            "error_count": len(validation_errors),
            "field_names": [
                ".".join(str(loc) for loc in error["loc"] if loc != "body")
                for error in validation_errors
            ],
        },
    )

    # Format validation errors into a more user-friendly structure
    errors: dict[str, Any] = {}
    for error in validation_errors:
        field_path = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        if field_path not in errors:
            errors[field_path] = []
        errors[field_path].append(error["msg"])

    problem = ProblemDetails(
        type="https://api.dilcore.ai/errors/validation-error",
        title="Validation Error",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Request validation failed. Please check the errors field for details.",
        instance=request.url.path,
        errors=errors,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )


def pydantic_validation_exception_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors.

    Args:
        request: The incoming request
        exc: The Pydantic validation exception

    Returns:
        JSONResponse with Problem Details format
    """
    validation_errors = exc.errors()
    # Log error count without exposing user input
    logger.warning(
        "Pydantic validation error occurred",
        extra={
            "path": request.url.path,
            "error_count": len(validation_errors),
            "field_names": [
                ".".join(str(loc) for loc in error["loc"]) for error in validation_errors
            ],
        },
    )

    # Format validation errors
    errors: dict[str, Any] = {}
    for error in validation_errors:
        field_path = ".".join(str(loc) for loc in error["loc"])
        if field_path not in errors:
            errors[field_path] = []
        errors[field_path].append(error["msg"])

    problem = ProblemDetails(
        type="https://api.dilcore.ai/errors/validation-error",
        title="Validation Error",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Data validation failed. Please check the errors field for details.",
        instance=request.url.path,
        errors=errors,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )


def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exceptions.

    Args:
        request: The incoming request
        exc: The unhandled exception

    Returns:
        JSONResponse with Problem Details format
    """
    logger.exception(
        "Unhandled exception: %s",
        str(exc),
        exc_info=True,
        extra={
            "path": request.url.path,
            "exception_type": type(exc).__name__,
        },
    )

    problem = ProblemDetails(
        type="https://api.dilcore.ai/errors/internal-server-error",
        title="Internal Server Error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred. Please try again later.",
        instance=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )
