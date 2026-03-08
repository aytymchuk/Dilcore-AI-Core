"""Tracing — LangSmith and OpenTelemetry setup.

Configure via environment variables:
    LANGCHAIN_TRACING_V2=true
    LANGCHAIN_API_KEY=<your-key>
    LANGCHAIN_PROJECT=<project-name>
    OTEL_EXPORTER_OTLP_ENDPOINT=<endpoint>
"""

from __future__ import annotations

import logging
import os

# Disable the auto-instrumentation for FastAPI and ASGI initialized by Azure Monitor because
# the SDK drops or ignores third-party nested exclusion settings for `exclude_spans`.
# We will manually instrument it in our main.py loop.
os.environ.setdefault("OTEL_PYTHON_DISABLED_INSTRUMENTATIONS", "fastapi,asgi")

logger = logging.getLogger(__name__)


# ruff: noqa: E402
from container import Container

_tracing_configured = False
_container: Container | None = None


def configure_tracing() -> None:
    """Configure LangSmith and OpenTelemetry tracing.

    LangSmith tracing is activated automatically when the
    ``LANGCHAIN_TRACING_V2`` environment variable is set to ``"true"``.
    OpenTelemetry is activated when `AZURE_APPLICATION_INSIGHTS_CONNECTION_STRING` is set.
    """
    global _tracing_configured, _container
    if _tracing_configured:
        return

    if os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true":
        logger.info(
            "LangSmith tracing enabled (project=%s)",
            os.getenv("LANGCHAIN_PROJECT", "default"),
        )
    else:
        logger.debug("LangSmith tracing is disabled")

    # Configure OpenTelemetry SDK and Azure Monitor setup using DI container
    _container = Container()
    _container.infrastructure.telemetry()

    _tracing_configured = True


def shutdown_tracing() -> None:
    """Shutdown tracing and perform cleanup."""
    global _tracing_configured, _container
    if not _tracing_configured or _container is None:
        return

    # dependency-injector resources can be shutdown via the container
    _container.shutdown_resources()
    _container = None
    _tracing_configured = False
    logger.info("Tracing telemetry shutdown complete.")
