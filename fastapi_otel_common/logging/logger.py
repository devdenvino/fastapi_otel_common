"""Logging configuration with OpenTelemetry integration.

Provides structured logging with OTLP export capabilities.
"""
import inspect
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from ..core.config import LOG_LEVEL

# Type variable for decorated function
F = TypeVar('F', bound=Callable[..., Awaitable[Any]])

# Configure basic logging
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(name)s] - %(message)s",
    datefmt="%Y-%m-%d:%H:%M:%S",
    level=LOG_LEVEL,
)


def setup_logger(service_name: str = "my-service") -> logging.Logger:
    """Configure and return a logger that exports logs to OTLP endpoint.
    
    Args:
        service_name: Name of the service for log identification
        
    Returns:
        logging.Logger: Configured logger instance with OTLP exporter
        
    Note:
        Requires OTEL_EXPORTER_OTLP_ENDPOINT environment variable.
    """
    import os
    
    # Get service configuration from environment
    service_name = os.getenv("SERVICE_NAME", service_name)
    service_version = os.getenv("SERVICE_VERSION", "1.0.0")
    otlp_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
    )
    
    # Define resource attributes
    resource = Resource.create(
        attributes={
            "service.name": service_name,
            "service.version": service_version
        }
    )

    # Configure LoggerProvider
    provider = LoggerProvider(resource=resource)

    # Configure OTLP exporter (point to jaeger-collector or OTEL collector)
    otlp_exporter = OTLPLogExporter(otlp_endpoint)

    # Attach processor
    provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))

    # Create logging handler for Python stdlib logging
    handler = LoggingHandler(logger_provider=provider, level=logging.NOTSET)

    # Create standard Python logger
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.DEBUG)

    # Formatter with requested format
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s [%(filename)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler.setFormatter(formatter)

    # Ensure only one handler (avoid duplicates)
    if not logger.handlers:
        logger.addHandler(handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.
    
    Args:
        name: Name for the logger (typically __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    return logger


def async_log(logger: logging.Logger, level: str, message: str) -> Callable[[F], F]:
    """Decorator to automatically log async function calls with arguments and results.
    
    Args:
        logger: Logger instance to use
        level: Log level ('debug', 'info', 'warning', 'error')
        message: Log message template with {arg_name} placeholders
        
    Returns:
        Callable: Decorated function
        
    Example:
        @async_log(logger, 'info', 'Called function with user={user_id}, result={result}')
        async def my_function(user_id: str) -> str:
            return "success"
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get the function's argument names and their values
            bound_args = inspect.signature(func).bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Create a format dictionary from the bound arguments
            format_dict = {key: value for key, value in bound_args.arguments.items()}

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

        return wrapper  # type: ignore

    return decorator
