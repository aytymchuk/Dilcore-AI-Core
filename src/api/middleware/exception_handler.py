"""Global exception handling middleware for Problem Details (RFC 7807)."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.schemas.errors import ProblemDetails
from shared.exceptions import AIAgentException

logger = logging.getLogger(__name__)


def create_problem_details(
    request: Request,
    problem_type: str,
    title: str,
    status_code: int,
    detail: str,
) -> ProblemDetails:
    """Create a Problem Details response object."""
    base_url = "https://api.dilcore.ai/problems"
    return ProblemDetails(
        type=f"{base_url}/{problem_type}",
        title=title,
        status=status_code,
        detail=detail,
        instance=request.url.path,
    )


async def ai_agent_exception_handler(request: Request, exc: AIAgentException) -> JSONResponse:
    """Handle custom AI Agent exceptions."""
    logger.error("AI Agent error: %s - %s", exc.problem_type, exc.message, exc_info=True)
    problem = create_problem_details(request, exc.problem_type, exc.title, exc.status_code, exc.message)
    return JSONResponse(status_code=exc.status_code, content=problem.model_dump())


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI validation errors."""
    error_details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        message = error["msg"]
        error_details.append(f"{field}: {message}" if field else message)
    detail = "Request validation failed: " + "; ".join(error_details)
    logger.warning("Validation error: %s", detail)
    problem = create_problem_details(
        request,
        "validation-error",
        "Request Validation Error",
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail,
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=problem.model_dump())


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
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
    detail = exc.detail if status_code < 500 else "An internal error occurred"
    logger.error("HTTP %d error: %s", status_code, exc.detail, exc_info=status_code >= 500)
    problem = create_problem_details(request, problem_type, title, status_code, detail)
    return JSONResponse(status_code=status_code, content=problem.model_dump())


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions."""
    logger.exception("Unhandled exception: %s", str(exc))
    problem = create_problem_details(
        request,
        "internal-error",
        "Internal Server Error",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "An unexpected error occurred while processing your request",
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=problem.model_dump())


def setup_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI application."""
    app.add_exception_handler(AIAgentException, ai_agent_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    logger.info("Exception handlers registered for Problem Details format")
