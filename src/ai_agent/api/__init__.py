"""API module with multi-agent routes."""

# Legacy routes (backward compatibility)
# New agent-specific routes
from .module_builder_routes import router as module_builder_router
from .persona_routes import router as persona_router
from .routes import health_router, router
from .streaming_routes import router as streaming_router

__all__ = [
    # Legacy (backward compatibility)
    "router",
    "streaming_router",
    "health_router",
    # Multi-agent routes
    "module_builder_router",
    "persona_router",
]
