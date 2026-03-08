import logging

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.sdk.resources import Resource

from application.abstractions.abc_tenant_provider import AbcTenantProvider
from application.abstractions.abc_user_id_provider import AbcUserIdProvider
from infrastructure.tracing.processors import (
    DependencyNameFixer,
    TenantLogFilter,
    TenantSpanProcessor,
    UserLogFilter,
)
from shared.config.settings import Settings

logger = logging.getLogger(__name__)


def setup_telemetry(tenant_provider: AbcTenantProvider, user_provider: AbcUserIdProvider, settings: Settings):
    """
    Configures Azure Monitor and attaches the custom processors.
    """
    connection_string = settings.azure_telemetry.application_insights_connection_string

    if connection_string:
        # Configure Azure Monitor Distro
        tenant_processor = TenantSpanProcessor(tenant_provider, user_provider)
        name_fixer = DependencyNameFixer()

        # Create explicit resource object for Azure Monitor
        resource = Resource.create(
            {
                "service.name": settings.application.name,
                "service.version": settings.application.version,
            }
        )

        def httpx_request_hook(span, request):
            """Hook to enrich httpx client span names with the target host."""
            if span.is_recording():
                span.update_name(f"{request.method} {request.url.host}")

        def urllib3_request_hook(span, method, url, _kwargs):
            """Hook to enrich urllib3 client span names with the target host."""
            if span.is_recording():
                # url is typically the host/netloc in urllib3 instrumentation
                span.update_name(f"{method} {url}")

        def urllib_request_hook(span, request):
            """Hook to enrich urllib client span names with the target host."""
            if span.is_recording():
                method = getattr(request, "method", "GET")
                url = getattr(request, "full_url", "")
                if url:
                    from urllib.parse import urlparse

                    try:
                        parsed = urlparse(str(url))
                        span.update_name(f"{method} {parsed.netloc}")
                    except Exception:
                        span.update_name(f"{method} {url}")

        configure_azure_monitor(
            connection_string=connection_string,
            span_processors=[tenant_processor, name_fixer],
            resource=resource,
            enable_live_metrics=False,
            instrumentation_options={
                # Suppress noisy ASGI and FastAPI low-level send/receive internal spans
                "fastapi": {"exclude_spans": ["receive", "send"]},
                "asgi": {"exclude_spans": ["receive", "send"]},
                "httpx": {"request_hook": httpx_request_hook},
                "urllib3": {"request_hook": urllib3_request_hook},
                "urllib": {"request_hook": urllib_request_hook},
            },
        )

        # Silence the very noisy Azure HTTP logging policy that prints request headers every time telemetry is exported
        logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)

        # Azure Monitor's configuration automatically attaches an OpenTelemetry LoggingHandler
        # to the root logger. We must find it and attach our custom filters to it so that
        # tenant.id and user.id are injected into python LogRecords before export.
        from opentelemetry.sdk._logs import LoggingHandler

        root_logger = logging.getLogger()
        tenant_filter = TenantLogFilter(tenant_provider)
        user_filter = UserLogFilter(user_provider)

        found_any = False
        for h in root_logger.handlers:
            if isinstance(h, LoggingHandler):
                h.addFilter(tenant_filter)
                h.addFilter(user_filter)
                found_any = True

        if not found_any:
            logger.warning(
                "OpenTelemetry LoggingHandler not found on root logger. "
                "Tenant and User log enrichment will not be applied."
            )

        logger.info(
            "Azure Monitor telemetry initialized for %s (%s) with custom processors.",
            settings.application.name,
            settings.application.version,
        )
    else:
        logger.warning("AZURE_APPLICATION_INSIGHTS_CONNECTION_STRING not found. Telemetry not configured.")
