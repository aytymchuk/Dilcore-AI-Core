from unittest.mock import MagicMock

from opentelemetry import trace

from app.core.context import get_tenant_id, get_user_id, tenant_id_var, user_id_var
from app.core.telemetry import TenantSpanProcessor


def test_context_variables_defaults():
    """Verify default values of context variables."""
    assert get_tenant_id() == "UNKNOWN"
    assert get_user_id() == "UNKNOWN"


def test_context_variables_set_get():
    """Verify setting and getting context variables."""
    t_token = tenant_id_var.set("test-tenant")
    u_token = user_id_var.set("test-user")

    try:
        assert get_tenant_id() == "test-tenant"
        assert get_user_id() == "test-user"
    finally:
        tenant_id_var.reset(t_token)
        user_id_var.reset(u_token)


def test_tenant_span_processor_injects_attributes():
    """Verify that TenantSpanProcessor injects attributes into spans."""
    t_token = tenant_id_var.set("span-tenant")
    u_token = user_id_var.set("span-user")

    try:
        processor = TenantSpanProcessor()
        span = MagicMock(spec=trace.Span)

        processor.on_start(span)

        span.set_attribute.assert_any_call("tenant.id", "span-tenant")
        span.set_attribute.assert_any_call("user.id", "span-user")
    finally:
        tenant_id_var.reset(t_token)
        user_id_var.reset(u_token)
