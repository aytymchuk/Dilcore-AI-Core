"""Telemetry configuration and context variables."""

import contextvars
import logging

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from application.abstractions.tenant_provider import ITenantProvider
from shared.config import get_settings

# Context variables for multitenancy
tenant_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("tenant_id_var", default="UNKNOWN")
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id_var", default="UNKNOWN")


def get_tenant_id() -> str:
    """Get the current tenant ID."""
    return tenant_id_var.get()


def get_user_id() -> str:
    """Get the current user ID."""
    return user_id_var.get()


class ContextTenantProvider(ITenantProvider):
    """Tenant provider implementation using context variables."""

    def get_tenant_id(self) -> str:
        return get_tenant_id()

    def get_user_id(self) -> str:
        return get_user_id()


class TenantSpanProcessor(SimpleSpanProcessor):
    """Custom span processor to inject tenant and user IDs into spans."""

    def __init__(self):
        # Initializing without an exporter
        pass

    def on_start(self, span: trace.Span, parent_context=None) -> None:
        """Inject tenant and user IDs into the span at start."""
        tenant_id = get_tenant_id()
        user_id = get_user_id()

        if span.is_recording():
            span.set_attribute("tenant.id", tenant_id)
            span.set_attribute("user.id", user_id)

    def on_end(self, span):
        """Override to avoid export logic, as we have no exporter."""
        pass

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis: int = 30000):
        return True


def setup_telemetry() -> None:
    """Configure Azure Monitor and add the TenantSpanProcessor."""
    settings = get_settings()

    # Disable uvicorn loggers to avoid duplication and structured log corruption
    logging.getLogger("uvicorn").handlers.clear()
    logging.getLogger("uvicorn.access").handlers.clear()

    # Configure Azure Monitor
    conn_str = settings.azure_application_insights_connection_string
    logger = logging.getLogger(__name__)

    if conn_str:
        try:
            configure_azure_monitor(connection_string=conn_str)
            logger.info("Azure Monitor OpenTelemetry configured successfully.")
        except ValueError as e:
            logger.warning("Could not configure Azure Monitor: %s", e)
    else:
        logger.debug("Skipping Azure Monitor configuration: empty connection string.")

    # Get active tracer provider and attach our processor
    provider = trace.get_tracer_provider()
    if hasattr(provider, "add_span_processor"):
        provider.add_span_processor(TenantSpanProcessor())
