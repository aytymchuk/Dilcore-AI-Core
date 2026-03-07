import logging
from unittest.mock import MagicMock

import pytest
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor

from application.abstractions.abc_tenant_provider import AbcTenantProvider
from application.abstractions.abc_user_context_provider import AbcUserIdProvider
from infrastructure.tracing.processors.log import TenantLogFilter, UserLogFilter


class TestAzureTelemetryFilters:
    @pytest.fixture
    def mock_tenant_provider(self):
        provider = MagicMock(spec=AbcTenantProvider)
        provider.get_tenant_id.return_value = "test-tenant-id"
        return provider

    @pytest.fixture
    def mock_user_provider(self):
        provider = MagicMock(spec=AbcUserIdProvider)
        provider.get_user_id.return_value = "test-user-id"
        return provider

    @pytest.fixture
    def log_handler(self, mock_tenant_provider, mock_user_provider):
        exporter = InMemoryLogRecordExporter()
        provider = LoggerProvider()
        provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))

        handler = LoggingHandler(level=logging.INFO, logger_provider=provider)
        handler.addFilter(TenantLogFilter(mock_tenant_provider))
        handler.addFilter(UserLogFilter(mock_user_provider))

        return handler, exporter

    def test_filters_inject_attributes(self, log_handler):
        handler, exporter = log_handler
        logger = logging.getLogger("test_telemetry")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        logger.info("Test message")

        # Get the exported logs
        logs = exporter.get_finished_logs()
        assert len(logs) == 1

        log_record = logs[0].log_record
        # standard python attributes are mapped to attributes in OTel LogRecord
        assert log_record.attributes["tenant.id"] == "test-tenant-id"
        assert log_record.attributes["user.id"] == "test-user-id"
