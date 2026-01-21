"""FastAPI application entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from scalar_fastapi import get_scalar_api_reference

from ai_agent.api import health_router, router, streaming_router
from ai_agent.config import get_settings
from ai_agent.middleware import setup_exception_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events.
    """
    settings = get_settings()
    logger.info("Starting %s...", settings.app_name)
    logger.info("Using model: %s", settings.openrouter.model)

    yield

    logger.info("Shutting down %s...", settings.app_name)


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    """Generate custom OpenAPI schema with enhanced error documentation.

    Args:
        app: The FastAPI application instance.

    Returns:
        Custom OpenAPI schema dictionary.
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add Problem Details schema to components
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}

    # Add Problem Details schema
    openapi_schema["components"]["schemas"]["ProblemDetails"] = {
        "type": "object",
        "required": ["type", "title", "status", "detail", "instance"],
        "properties": {
            "type": {
                "type": "string",
                "description": "A URI reference that identifies the problem type",
                "example": "https://api.dilcore.ai/problems/validation-error",
            },
            "title": {
                "type": "string",
                "description": "A short, human-readable summary of the problem type",
                "example": "Validation Error",
            },
            "status": {
                "type": "integer",
                "description": "The HTTP status code",
                "minimum": 400,
                "maximum": 599,
                "example": 400,
            },
            "detail": {
                "type": "string",
                "description": "A human-readable explanation specific to this occurrence",
                "example": "The request body contains invalid data",
            },
            "instance": {
                "type": "string",
                "description": "A URI reference that identifies the specific occurrence",
                "example": "/api/v1/metadata/generate",
            },
        },
        "example": {
            "type": "https://api.dilcore.ai/problems/validation-error",
            "title": "Validation Error",
            "status": 422,
            "detail": "prompt: field required",
            "instance": "/api/v1/metadata/generate",
        },
    }

    # Add error response examples to paths
    error_examples = {
        "400": {
            "type": "https://api.dilcore.ai/problems/bad-request",
            "title": "Bad Request",
            "status": 400,
            "detail": "The request could not be understood",
            "instance": "/api/v1/metadata/generate",
        },
        "422": {
            "type": "https://api.dilcore.ai/problems/validation-error",
            "title": "Request Validation Error",
            "status": 422,
            "detail": "prompt: ensure this value has at most 4000 characters",
            "instance": "/api/v1/metadata/generate",
        },
        "500": {
            "type": "https://api.dilcore.ai/problems/generation-error",
            "title": "Template Generation Error",
            "status": 500,
            "detail": "An unexpected error occurred during template generation",
            "instance": "/api/v1/metadata/generate",
        },
        "502": {
            "type": "https://api.dilcore.ai/problems/llm-provider-error",
            "title": "LLM Provider Error",
            "status": 502,
            "detail": "Unable to communicate with AI provider",
            "instance": "/api/v1/metadata/generate",
        },
    }

    # Enhance error responses in paths
    for path_data in openapi_schema.get("paths", {}).values():
        for operation in path_data.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            for status_code, example in error_examples.items():
                if status_code in responses:
                    responses[status_code]["content"] = {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ProblemDetails"},
                            "example": example,
                        }
                    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "AI Agent for generating structured JSON templates "
            "using LangChain and OpenRouter"
        ),
        version="0.1.0",
        docs_url=None,  # Disable default Swagger UI
        redoc_url=None,  # Disable ReDoc
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup global exception handlers (Problem Details format)
    setup_exception_handlers(app)

    # Include API routes
    app.include_router(health_router)
    app.include_router(router)
    app.include_router(streaming_router)

    # Configure custom OpenAPI schema with enhanced error documentation
    app.openapi = lambda: custom_openapi(app)

    # Scalar API documentation
    @app.get("/scalar", include_in_schema=False)
    async def scalar_docs():
        """Serve Scalar API documentation."""
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            title=f"{settings.app_name} - API Reference",
        )

    @app.get("/", include_in_schema=False)
    async def root():
        """Root endpoint redirecting to docs."""
        return {"message": "Welcome to AI Template Agent", "docs": "/scalar"}

    return app


# Create app instance
app = create_app()
