from opentelemetry import trace
from opentelemetry.sdk.trace import SpanProcessor

from application.abstractions.abc_tenant_provider import AbcTenantProvider
from application.abstractions.abc_user_id_provider import AbcUserIdProvider


class TenantSpanProcessor(SpanProcessor):
    """
    Custom SpanProcessor that injects tenant_id and user_id attributes
    into every span when it starts.
    """

    def __init__(self, tenant_provider: AbcTenantProvider, user_provider: AbcUserIdProvider):
        self._tenant_provider = tenant_provider
        self._user_provider = user_provider

    def on_start(self, span: trace.Span, parent_context=None):
        """Retrieve IDs from context and set as span attributes."""

        tenant_id = self._tenant_provider.get_tenant_id()
        user_id = self._user_provider.get_user_id()

        span.set_attribute("tenant.id", tenant_id)
        span.set_attribute("user.id", user_id)


class DependencyNameFixer(SpanProcessor):
    """
    Fixes empty or missing span names (e.g. from urllib3 tracing) which show up
    as "N/A" in Application Insights.
    """

    def on_start(self, span: trace.Span, parent_context=None):
        """
        Fixes empty or missing span names at the start of the span.
        Note: Many attributes are set after the span starts, so this is
        best-effort here. Specific instrumentor hooks are preferred.
        """
        if not span.is_recording():
            return

        name = getattr(span, "name", "")
        # Azure often drops spans without descriptive names into "N/A"
        # urllib3 sometimes just names its spans "GET" or "POST", not the full URL.
        if (
            not name
            or name in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "HTTP", "HTTP Request")
            or name.startswith("HTTP ")
        ):
            attrs: dict = getattr(span, "attributes", {}) or {}

            # Use current name as a hint if it's a standard method
            method_hint = name if name in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS") else None

            # Prioritize standard OTel attributes (modern first, then legacy)
            method = (
                attrs.get("http.request.method")
                or attrs.get("http.method")
                or method_hint
                or getattr(getattr(span, "kind", None), "name", "HTTP")
            )
            if method == "CLIENT":
                method = "HTTP"

            # Host extraction from various semantic conventions
            host = (
                attrs.get("server.address")
                or attrs.get("network.peer.address")
                or attrs.get("http.host")
                or attrs.get("peer.service")
            )

            # If no host, try parsing it from full URL
            if not host:
                url = attrs.get("url.full") or attrs.get("http.url", "")
                if url:
                    from urllib.parse import urlparse

                    try:
                        parsed = urlparse(str(url))
                        host = parsed.netloc or parsed.path.split("/")[0]
                    except Exception:
                        pass

            new_name = f"{method} {host}" if host else f"{method} Dependency"
            span.update_name(new_name)

    def on_end(self, span: trace.Span) -> None:
        pass
