"""Global exception handling middleware for Problem Details (RFC 7807)."""

import logging
from typing import Callable

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..exceptions import AIAgentException
from ..schemas.errors import ProblemDetails

logger = logging.getLogger(__name__)


def create_problem_details(
    request: Request,
    problem_type: str,
    title: str,
    status_code: int,
    detail: str,
) -> ProblemDetails:
    """Create a Problem Details response.

    Args:
        request: The FastAPI request object
        problem_type: The problem type identifier
        title: Short summary of the problem
        status_code: HTTP status code
        detail: Detailed description of the problem

    Returns:
        ProblemDetails object
    """
    base_url = "https://api.dilcore.ai/problems"
    return ProblemDetails(
        type=f"{base_url}/{problem_type}",
        title=title,
        status=status_code,
        detail=detail,
        instance=request.url.path,
    )


async def ai_agent_exception_handler(
    request: Request,
    exc: AIAgentException,
) -> JSONResponse:
    """Handle custom AI Agent exceptions.

    Args:
        request: The incoming request
        exc: The AI Agent exception

    Returns:
        JSONResponse with Problem Details format
    """
    logger.error(
        "AI Agent error: %s - %s",
        exc.problem_type,
        exc.message,
        exc_info=True,
    )

    problem = create_problem_details(
        request=request,
        problem_type=exc.problem_type,
        title=exc.title,
        status_code=exc.status_code,
        detail=exc.message,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle FastAPI validation errors.

    Args:
        request: The incoming request
        exc: The validation error

    Returns:
        JSONResponse with Problem Details format
    """
    # Extract validation errors without exposing internal details
    error_details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        message = error["msg"]
        error_details.append(f"{field}: {message}" if field else message)

    detail = "Request validation failed: " + "; ".join(error_details)

    logger.warning("Validation error: %s", detail)

    problem = create_problem_details(
        request=request,
        problem_type="validation-error",
        title="Request Validation Error",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=detail,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem.model_dump(),
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Handle HTTP exceptions.

    Args:
        request: The incoming request
        exc: The HTTP exception

    Returns:
        JSONResponse with Problem Details format
    """
    # Map status codes to problem types
    status_code = exc.status_code
    problem_type_map = {
        400: "bad-request",
        401: "unauthorized",
        403: "forbidden",
        404: "not-found",
        405: "method-not-allowed",
        409: "conflict",
        429: "too-many-requests",
    }

    problem_type = problem_type_map.get(status_code, "http-error")
    title = exc.detail if status_code < 500 else "Internal Server Error"

    # Don't expose internal error details for 5xx errors
    detail = exc.detail if status_code < 500 else "An internal error occurred"

    logger.error(
        "HTTP %d error: %s",
        status_code,
        exc.detail,
        exc_info=status_code >= 500,
    )

    problem = create_problem_details(
        request=request,
        problem_type=problem_type,
        title=title,
        status_code=status_code,
        detail=detail,
    )

    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(),
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle all unhandled exceptions.

    This is the catch-all handler that ensures no service-specific
    information is leaked in error responses.

    Args:
        request: The incoming request
        exc: The unhandled exception

    Returns:
        JSONResponse with Problem Details format
    """
    logger.exception("Unhandled exception: %s", str(exc))

    # Never expose internal exception details to clients
    problem = create_problem_details(
        request=request,
        problem_type="internal-error",
        title="Internal Server Error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred while processing your request",
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem.model_dump(),
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI application.

    This function configures global exception handling to ensure all errors
    are returned in Problem Details (RFC 7807) format.

    Args:
        app: The FastAPI application instance
    """
    # Custom AI Agent exceptions
    app.add_exception_handler(AIAgentException, ai_agent_exception_handler)

    # FastAPI validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Catch-all for unhandled exceptions
    app.add_exception_handler(Exception, unhandled_exception_handler)

    logger.info("Exception handlers registered for Problem Details format")
