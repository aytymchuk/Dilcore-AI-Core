"""API module."""

from .routes import router
from .streaming_routes import router as streaming_router

__all__ = ["router", "streaming_router"]

