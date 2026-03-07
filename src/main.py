"""FastAPI application entry point."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from infrastructure.tracing import configure_tracing

# VERY IMPORTANT: Configure tracing before importing FastAPI
# This ensures that OpenTelemetry properly instruments the FastAPI application
configure_tracing()

# ruff: noqa: E402
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.controllers import blueprints_router, health_router
from api.controllers.auth_dependencies import verify_token
from api.controllers.users import users_router
from api.middleware import setup_exception_handlers
from api.openapi import setup_openapi
from infrastructure.checkpoint.document_checkpointer import close_checkpointer
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
    logger.info("Starting %s...", settings.app_name)
    logger.info("Using model: %s", settings.openrouter.model)
    yield
    close_checkpointer()
    logger.info("Shutting down %s...", settings.app_name)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI Agent for handling user intents and creating custom blueprints.",
        version="0.2.0",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials="*" not in settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    setup_exception_handlers(app)

    # API routes
    app.include_router(health_router)
    app.include_router(users_router)  # /api/v1/users
    app.include_router(blueprints_router, dependencies=[Depends(verify_token)])  # /api/v1/blueprints

    setup_openapi(app)

    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": "Welcome to Dilcore AI Agent", "docs": "/scalar"}

    return app


app = create_app()
