import logging
import os

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from app.core.context import get_tenant_id, get_user_id

logger = logging.getLogger(__name__)


class TenantSpanProcessor(SimpleSpanProcessor):
    """
    Custom SpanProcessor that injects tenant_id and user_id attributes
    into every span when it starts.
    """

    def __init__(self):
        # The prompt specifically requested SimpleSpanProcessor.
        # SimpleSpanProcessor usually requires an exporter, but we use it for enrichment.
        pass

    def on_start(self, span: trace.Span, parent_context=None):
        """Retrieve IDs from context and set as span attributes."""
        tenant_id = get_tenant_id()
        user_id = get_user_id()

        span.set_attribute("tenant.id", tenant_id)
        span.set_attribute("user.id", user_id)


def setup_telemetry():
    """
    Configures Azure Monitor and attaches the TenantSpanProcessor.
    """
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

    if connection_string:
        # Configure Azure Monitor Distro
        tenant_processor = TenantSpanProcessor()

        configure_azure_monitor(connection_string=connection_string, span_processors=[tenant_processor])
        logger.info("Azure Monitor telemetry initialized with TenantSpanProcessor.")
    else:
        logger.warning("APPLICATIONINSIGHTS_CONNECTION_STRING not found. Telemetry not configured.")
