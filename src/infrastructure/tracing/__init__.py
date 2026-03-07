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

logger = logging.getLogger(__name__)


def configure_tracing() -> None:
    """Configure LangSmith and OpenTelemetry tracing.

    LangSmith tracing is activated automatically when the
    ``LANGCHAIN_TRACING_V2`` environment variable is set to ``"true"``.
    OpenTelemetry configuration is a placeholder for future integration.
    """
    if os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true":
        logger.info(
            "LangSmith tracing enabled (project=%s)",
            os.getenv("LANGCHAIN_PROJECT", "default"),
        )
    else:
        logger.debug("LangSmith tracing is disabled")

    # Configure OpenTelemetry SDK and Azure Monitor setup
    from infrastructure.telemetry import setup_telemetry

    setup_telemetry()
