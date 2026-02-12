"""Logging configuration with OpenTelemetry and Loguru integration.

Provides structured logging with OTLP export capabilities and rich formatting.
"""
import inspect
import logging
import os
import sys
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from loguru import logger
from opentelemetry import trace as otel_trace
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

from ..core.config import LOG_LEVEL

# Type variable for decorated function
F = TypeVar('F', bound=Callable[..., Awaitable[Any]])

class InterceptHandler(logging.Handler):
    """Logs from standard logging are redirected to Loguru."""
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def setup_logger(service_name: str = "my-service") -> Any:
    """Configure and return a logger that exports logs to OTLP endpoint using Loguru.
    
    Args:
        service_name: Name of the service for log identification
        
    Returns:
        The configured loguru logger
    """
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

    # Configure LoggerProvider for OpenTelemetry
    provider = LoggerProvider(resource=resource)
    
    # Configure OTLP exporter
    # insecure=True is often needed for local testing without TLS
    otlp_exporter = OTLPLogExporter(endpoint=otlp_endpoint, insecure=True)

    # Attach processor
    provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))

    # Create handler for OpenTelemetry
    # This handler will receive logs and export them via OTEL
    otel_handler = LoggingHandler(logger_provider=provider)

    # Configure Loguru
    # Remove default handler
    logger.remove()
    
    # Define a filter/patcher to add trace context
    def otel_patcher(record):
        span_context = otel_trace.get_current_span().get_span_context()
        if span_context.is_valid:
            record["extra"]["trace_id"] = format(span_context.trace_id, "032x")
            record["extra"]["span_id"] = format(span_context.span_id, "016x")
        else:
            record["extra"]["trace_id"] = "0" * 32
            record["extra"]["span_id"] = "0" * 16

    # Add stdout handler with rich formatting including trace context
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <magenta>trace_id={extra[trace_id]}</magenta> <magenta>span_id={extra[span_id]}</magenta> - <level>{message}</level>",
        level=LOG_LEVEL,
        colorize=True,
    )
    
    # Configure the global logger with the patcher
    global_logger = logger.patch(otel_patcher)

    # Add OTEL sink
    # Loguru can use a logging.Handler as a sink
    global_logger.add(otel_handler, level=LOG_LEVEL)

    # Optional: Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Ensure uvicorn logs are also intercepted if used
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    return global_logger


def get_logger(name: str) -> Any:
    """Get a logger instance. With Loguru, we typically just use the global logger,
    but we can bind the name for compatibility.
    
    Args:
        name: Name for the logger
        
    Returns:
        A logger instance bound with the name
    """
    class LoggerWrapper:
        def __init__(self, logger_instance: Any):
            self._logger = logger_instance

        def _log(self, level: str, msg: str, *args: Any, **kwargs: Any) -> None:
            extra = kwargs.pop("extra", {})
            log_instance = self._logger.bind(**extra).opt(depth=2)
            getattr(log_instance, level)(msg, *args, **kwargs)

        def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
            self._log("debug", msg, *args, **kwargs)

        def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
            self._log("info", msg, *args, **kwargs)

        def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
            self._log("warning", msg, *args, **kwargs)

        def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
            self._log("error", msg, *args, **kwargs)

        def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
            self._log("critical", msg, *args, **kwargs)

        def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
            self._log("exception", msg, *args, **kwargs)

        def bind(self, **kwargs: Any) -> "LoggerWrapper":
            return LoggerWrapper(self._logger.bind(**kwargs).opt(depth=2))

    return LoggerWrapper(logger.bind(name=name))


def async_log(logger_instance: Any, level: str, message: str) -> Callable[[F], F]:
    """Decorator to automatically log async function calls with arguments and results.
    
    Args:
        logger_instance: Logger instance to use (loguru logger or bound logger)
        level: Log level ('debug', 'info', 'warning', 'error')
        message: Log message template with {arg_name} placeholders
        
    Returns:
        Callable: Decorated function
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
            try:
                result = await func(*args, **kwargs)
                # Add the result to the format dictionary
                format_dict["result"] = result
                # Format and log the success message
                log_message = message.format(**format_dict)
                getattr(logger_instance, level.lower())(log_message)
                return result
            except Exception as e:
                # Log the exception if one occurs
                logger_instance.exception(f"Exception in {func.__name__}: {e}")
                raise

        return wrapper  # type: ignore

    return decorator
