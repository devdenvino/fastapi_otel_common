import os
import inspect
import logging
from functools import wraps
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from ..core.config import LOG_LEVEL


# Configure logging
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(name)s] - %(message)s",
    datefmt="%Y-%m-%d:%H:%M:%S",
    level=LOG_LEVEL,
)


def setup_logger(service_name: str = "my-service") -> logging.Logger:
    """
    Not implemented yet.
    Configure and return a logger that exports logs to Jaeger via OTLP.
    """
    # Define resource attributes (service name important for Jaeger)0
    # Set up a basic Python logger
    # The LoggingInstrumentor will ensure that this logger's output
    # includes the trace and span IDs when inside a traced operation.
    service_name = os.getenv("SERVICE_NAME", "changeme")
    service_version = os.getenv("SERVICE_VERSION", "changeme")
    otlp_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    resource = Resource.create(
        attributes={"service.name": service_name,
                    "service.version": service_version}
    )
    # print(otlp_endpoint)
    # LoggingInstrumentor().instrument(set_logging_format=True)
    # otlp_log_exporter = OTLPLogExporter(endpoint=otlp_endpoint)
    # processor = BatchLogRecordProcessor(otlp_log_exporter)

    # logger_provider = LoggerProvider(resource=resource)
    # logger_provider.add_log_record_processor(processor)
    # # logging.setLoggerClass(logging.getLoggerClass())

    # otel_handler = LoggingHandler(level=LOG_LEVEL, logger_provider=logger_provider)
    # formatter = logging.Formatter(
    #     '%(asctime)s - %(name)s - %(levelname)s - %(message)s - [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s]')
    # otel_handler.setFormatter(formatter)

    # Configure LoggerProvider
    provider = LoggerProvider(resource=resource)

    # Configure OTLP exporter (point this to jaeger-collector or OTEL collector)
    otlp_exporter = OTLPLogExporter(
        otlp_endpoint
        # endpoint="http://localhost:4317", # default gRPC endpoint, uncomment if needed
        # insecure=True
    )

    # Attach processor
    provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))

    # Create logging handler for Python stdlib logging
    handler = LoggingHandler(logger_provider=provider, level=logging.NOTSET)

    # Create standard Python logger
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.DEBUG)

    # Formatter with requested format (includes filename via %(name)s)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s [%(filename)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler.setFormatter(formatter)

    # Ensure only one handler (avoid duplicates)
    if not logger.handlers:
        logger.addHandler(handler)

    return logger


def get_logger(name: str):
    logger = logging.getLogger(name)
    # Get the root logger and add the handler
    # logger.addHandler(otel_handler)
    logger.setLevel(LOG_LEVEL)
    return logger


def async_log(logger, level, message):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get the function's argument names and their values
            bound_args = inspect.signature(func).bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Create a format dictionary from the bound arguments
            format_dict = {key: value for key,
                           value in bound_args.arguments.items()}

            # Call the original function and get the result
            result = await func(*args, **kwargs)

            # Add the result to the format dictionary
            format_dict["result"] = result

            # Format the log message
            log_message = message.format(**format_dict)

            # Log the message at the specified level
            getattr(logger, level)(log_message)

            # Return the original result
            return result

        return wrapper

    return decorator
