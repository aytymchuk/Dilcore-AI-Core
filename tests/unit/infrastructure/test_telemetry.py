from opentelemetry.sdk.trace import TracerProvider

from infrastructure.telemetry import (
    ContextTenantProvider,
    TenantSpanProcessor,
    get_tenant_id,
    get_user_id,
    tenant_id_var,
    user_id_var,
)


def test_context_variables_default_values():
    assert get_tenant_id() == "UNKNOWN"
    assert get_user_id() == "UNKNOWN"


def test_context_variables_set_get():
    tenant_token = tenant_id_var.set("test_tenant_123")
    user_token = user_id_var.set("test_user_456")

    try:
        assert get_tenant_id() == "test_tenant_123"
        assert get_user_id() == "test_user_456"

        provider = ContextTenantProvider()
        assert provider.get_tenant_id() == "test_tenant_123"
        assert provider.get_user_id() == "test_user_456"
    finally:
        tenant_id_var.reset(tenant_token)
        user_id_var.reset(user_token)


def test_tenant_span_processor_attributes():
    processor = TenantSpanProcessor()

    # Setup test trace provider with our processor
    provider = TracerProvider()
    provider.add_span_processor(processor)
    tracer = provider.get_tracer("test.tracer")

    # Set context values
    tenant_token = tenant_id_var.set("span_tenant_id")
    user_token = user_id_var.set("span_user_id")

    try:
        # Create a span in the tracer
        with tracer.start_as_current_span("test_span") as span:
            assert span.is_recording()

        # The telemetry is recorded, we can inspect via a custom exporter but
        # let's just use an internal check since we injected the attributes via processor
    finally:
        tenant_id_var.reset(tenant_token)
        user_id_var.reset(user_token)


class MockSpan:
    def __init__(self):
        self.attributes = {}
        self._is_recording = True

    def is_recording(self):
        return self._is_recording

    def set_attribute(self, key, value):
        self.attributes[key] = value


def test_tenant_span_processor_injects_attributes():
    tenant_token = tenant_id_var.set("unit_test_tenant")
    user_token = user_id_var.set("unit_test_user")

    try:
        processor = TenantSpanProcessor()
        span = MockSpan()

        processor.on_start(span)

        assert span.attributes.get("tenant.id") == "unit_test_tenant"
        assert span.attributes.get("user.id") == "unit_test_user"
    finally:
        tenant_id_var.reset(tenant_token)
        user_id_var.reset(user_token)
