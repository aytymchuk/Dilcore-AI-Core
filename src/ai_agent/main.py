"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from ai_agent.api import health_router, router, streaming_router
from ai_agent.config import get_settings

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


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI Agent for generating structured JSON templates using LangChain and OpenRouter",
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

    # Include API routes
    app.include_router(health_router)
    app.include_router(router)
    app.include_router(streaming_router)

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
