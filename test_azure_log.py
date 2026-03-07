import logging

from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter
from azure.monitor.opentelemetry.exporter.export.logs._exporter import _get_log_export_result
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
from opentelemetry.sdk.resources import Resource


# Custom Export to inspect Envelope
class DebugAzureExporter(AzureMonitorLogExporter):
    def export(self, batch, **kwargs):
        envelopes = [self._log_to_envelope(log) for log in batch]
        for env in envelopes:
            print("ENVELOPE DATA:")
            print("baseType:", env.data.base_type)
            print("baseData properties:", env.data.base_data.properties)
        return _get_log_export_result(1)


resource = Resource.create({"service.name": "test"})
provider = LoggerProvider(resource=resource)
provider.add_log_record_processor(
    SimpleLogRecordProcessor(
        DebugAzureExporter(connection_string="InstrumentationKey=00000000-0000-0000-0000-000000000000")
    )
)
set_logger_provider(provider)

handler = LoggingHandler(level=logging.NOTSET, logger_provider=provider)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)

# Run test
print("--- TEST 1: Extra attributes ---")
logging.info("This is a test message", extra={"tenant.id": "my-test-tenant-1", "user.id": "my-test-user-1"})

print("--- TEST 2: Filter on handler ---")


class MyFilter(logging.Filter):
    def filter(self, record):
        record.tenant_id = "my-test-tenant-2"
        setattr(record, "user.id", "my-test-user-2")
        return True


handler.addFilter(MyFilter())
logging.info("This is a filtered message")
