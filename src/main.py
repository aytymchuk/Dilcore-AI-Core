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

from api.controllers import blueprints_router, health_router, persona_router, streaming_router
from api.middleware import setup_exception_handlers
from infrastructure.tracing import configure_tracing
from shared.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()
    configure_tracing()
    logger.info("Starting %s...", settings.app_name)
    logger.info("Using model: %s", settings.openrouter.model)
    yield
    logger.info("Shutting down %s...", settings.app_name)


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    """Generate custom OpenAPI schema with enhanced error documentation."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema.setdefault("components", {}).setdefault("schemas", {})["ProblemDetails"] = {
        "type": "object",
        "required": ["type", "title", "status", "detail", "instance"],
        "properties": {
            "type": {"type": "string", "example": "https://api.dilcore.ai/problems/validation-error"},
            "title": {"type": "string", "example": "Validation Error"},
            "status": {"type": "integer", "minimum": 400, "maximum": 599, "example": 400},
            "detail": {"type": "string", "example": "The request body contains invalid data"},
            "instance": {"type": "string", "example": "/api/v1/blueprints/generate"},
        },
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI Agent for generating structured JSON templates using LangChain, LangGraph, and OpenRouter.",
        version="0.2.0",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    setup_exception_handlers(app)

    # API routes
    app.include_router(health_router)
    app.include_router(blueprints_router)  # /api/v1/blueprints
    app.include_router(streaming_router)  # /api/v1/metadata (legacy compat)
    app.include_router(persona_router)  # /api/v1/persona

    app.openapi = lambda: custom_openapi(app)  # noqa: E731

    @app.get("/scalar", include_in_schema=False)
    async def scalar_docs():
        return get_scalar_api_reference(openapi_url=app.openapi_url, title=f"{settings.app_name} - API Reference")

    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": "Welcome to Dilcore AI Agent", "docs": "/scalar"}

    return app


app = create_app()
