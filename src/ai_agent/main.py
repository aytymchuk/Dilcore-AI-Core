"""Main FastAPI application module.

This module creates and configures the FastAPI application with
RFC 7807 Problem Details error handling.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError as PydanticValidationError

from ai_agent.api import exception_handlers
from ai_agent.api.routes import router as api_router
from ai_agent.exceptions import AIAgentException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    logger.info("Starting AI Agent API")
    yield
    logger.info("Shutting down AI Agent API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Dilcore AI Core API",
        description="AI Agent API with RFC 7807 Problem Details error handling",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register exception handlers
    app.add_exception_handler(
        AIAgentException,
        exception_handlers.ai_agent_exception_handler,
    )
    app.add_exception_handler(
        HTTPException,
        exception_handlers.http_exception_handler,
    )
    app.add_exception_handler(
        RequestValidationError,
        exception_handlers.validation_exception_handler,
    )
    app.add_exception_handler(
        PydanticValidationError,
        exception_handlers.pydantic_validation_exception_handler,
    )
    app.add_exception_handler(
        Exception,
        exception_handlers.unhandled_exception_handler,
    )

    # Include routers
    app.include_router(api_router, prefix="/api/v1")

    logger.info("FastAPI application created successfully")
    return app


# Create the app instance
app = create_app()


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Root endpoint.

    Returns:
        Welcome message with API documentation link
    """
    return {
        "message": "Welcome to Dilcore AI Core API",
        "docs": "/docs",
        "version": "0.1.0",
    }
