import logging

from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import ConsoleLogExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.resources import Resource

if __name__ == "__main__":
    # Setup
    resource = Resource.create({"service.name": "test"})
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(SimpleLogRecordProcessor(ConsoleLogExporter()))
    set_logger_provider(logger_provider)

    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    # Test 1
    logging.info("Test message 1 with custom properties", extra={"tenant.id": "my-tenant", "user.id": "my-user"})

    # Test 2
    logger = logging.getLogger(__name__)
    logger.info(
        "Test message 2 with custom properties",
        extra={"custom_dimensions": {"tenant.id": "my-tenant", "user.id": "my-user"}},
    )

    # Test 3: Log filter
    class MyFilter(logging.Filter):
        def filter(self, record):
            record.attributes = {"tenant.id": "my-tenant", "user.id": "my-user"}
            return True

    handler.addFilter(MyFilter())
    logger.info("Test message 3 with filter")

    # Test 4: Another Log filter attempt
    class MyFilter2(logging.Filter):
        def filter(self, record):
            if not hasattr(record, "custom_dimensions"):
                record.custom_dimensions = {}
            record.custom_dimensions["tenant.id"] = "my-tenant"
            return True

    handler.removeFilter(handler.filters[0])
    handler.addFilter(MyFilter2())
    logger.info("Test message 4 with custom_dimensions parameter")
