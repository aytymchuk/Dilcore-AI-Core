from unittest.mock import MagicMock

from opentelemetry import trace

from infrastructure.tenant_provider import HeaderTenantProvider, _tenant_id_var
from infrastructure.tracing.processors.log import TenantLogFilter, UserLogFilter
from infrastructure.tracing.telemetry import TenantSpanProcessor
from infrastructure.user_provider import ContextUserProvider, set_user_id
from shared.constants import UNKNOWN_CONTEXT_VALUE


def test_context_variables_defaults():
    """Verify default values of context variables."""
    assert HeaderTenantProvider().get_tenant_id() == UNKNOWN_CONTEXT_VALUE
    assert ContextUserProvider().get_user_id() == UNKNOWN_CONTEXT_VALUE


def test_context_variables_set_get():
    """Verify setting and getting context variables."""
    token = _tenant_id_var.set("test-tenant")
    set_user_id("test-user")

    try:
        assert HeaderTenantProvider().get_tenant_id() == "test-tenant"
        assert ContextUserProvider().get_user_id() == "test-user"
    finally:
        _tenant_id_var.reset(token)
        set_user_id(UNKNOWN_CONTEXT_VALUE)


def test_tenant_span_processor_injects_attributes():
    """Verify that TenantSpanProcessor injects attributes into spans."""
    token = _tenant_id_var.set("span-tenant")
    set_user_id("span-user")

    try:
        tenant_provider = HeaderTenantProvider()
        user_provider = ContextUserProvider()
        processor = TenantSpanProcessor(tenant_provider, user_provider)
        span = MagicMock(spec=trace.Span)

        processor.on_start(span)

        span.set_attribute.assert_any_call("tenant.id", "span-tenant")
        span.set_attribute.assert_any_call("user.id", "span-user")
    finally:
        _tenant_id_var.reset(token)
        set_user_id(UNKNOWN_CONTEXT_VALUE)


def test_tenant_log_filter_injects_attributes():
    """Verify that TenantLogFilter injects tenant.id into standard log records."""
    token = _tenant_id_var.set("log-tenant")

    try:
        tenant_provider = HeaderTenantProvider()
        filter_instance = TenantLogFilter(tenant_provider)

        import logging

        log_record = logging.LogRecord("test", logging.INFO, "test.py", 1, "test message", None, None)

        assert filter_instance.filter(log_record) is True
        assert getattr(log_record, "tenant.id", None) == "log-tenant"
        assert getattr(log_record, "user.id", None) is None
    finally:
        _tenant_id_var.reset(token)


def test_user_log_filter_injects_attributes():
    """Verify that UserLogFilter injects user.id into standard log records."""
    set_user_id("log-user")

    try:
        user_provider = ContextUserProvider()
        filter_instance = UserLogFilter(user_provider)

        import logging

        log_record = logging.LogRecord("test", logging.INFO, "test.py", 1, "test message", None, None)

        assert filter_instance.filter(log_record) is True
        assert getattr(log_record, "user.id", None) == "log-user"
        assert getattr(log_record, "tenant.id", None) is None
    finally:
        set_user_id(UNKNOWN_CONTEXT_VALUE)
