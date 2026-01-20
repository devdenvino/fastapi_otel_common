"""OpenTelemetry tracing and metrics configuration and utilities.

Provides distributed tracing with automatic context propagation and metrics collection.
"""
import os
import traceback
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from opentelemetry import trace, metrics
from opentelemetry.context import attach, detach
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.propagate import extract
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.trace import Status, StatusCode

from ..logging.logger import get_logger

logger = get_logger(__name__)

# Global tracer provider reference for proper shutdown
_tracer_provider = None
_is_shutting_down = False


def setup_tracer() -> None:
    """Configure OpenTelemetry tracer with OTLP exporter.
    
    Reads configuration from environment variables:
    - SERVICE_NAME: Name of the service (default: 'changeme')
    - SERVICE_VERSION: Version of the service (default: 'changeme')
    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (only used if OTEL_EXPORTER_OTLP_TRACES_ENDPOINT is not set)
    - OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: OTLP traces endpoint (if not set, OTLP export is disabled)
    - OTEL_BSP_EXPORT_TIMEOUT: Export timeout in milliseconds (default: 5000)
    - OTEL_BSP_SCHEDULE_DELAY: Delay between exports in milliseconds (default: 5000)
    """
    global _tracer_provider
    
    service_name = os.getenv("SERVICE_NAME", "changeme")
    service_version = os.getenv("SERVICE_VERSION", "changeme")
    resource = Resource.create(
        attributes={"service.name": service_name, "service.version": service_version}
    )

    _tracer_provider = TracerProvider(resource=resource)
    
    # Check if OTLP export is enabled
    otlp_traces_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    if otlp_traces_endpoint:
        logger.info(f"Configuring OTLP trace exporter with endpoint: {otlp_traces_endpoint}")
        
        # Configure timeouts to prevent hanging during shutdown
        export_timeout_millis = int(os.getenv("OTEL_BSP_EXPORT_TIMEOUT", "5000"))
        schedule_delay_millis = int(os.getenv("OTEL_BSP_SCHEDULE_DELAY", "5000"))
        
        # Determine if endpoint is insecure (http vs https)
        insecure = otlp_traces_endpoint.startswith("http://")
        
        processor = BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=otlp_traces_endpoint,
                timeout=export_timeout_millis // 1000,  # Convert to seconds
                insecure=insecure
            ),
            schedule_delay_millis=schedule_delay_millis,
            export_timeout_millis=export_timeout_millis,
            max_export_batch_size=512,
            max_queue_size=2048
        )
        _tracer_provider.add_span_processor(processor)
    else:
        logger.info("OTLP trace export disabled (OTEL_EXPORTER_OTLP_TRACES_ENDPOINT not set)")
    
    trace.set_tracer_provider(_tracer_provider)


def shutdown_tracer(timeout_millis: int = 5000) -> None:
    """Shutdown the tracer provider and flush pending spans.
    
    This should be called during application shutdown to ensure all spans
    are exported and resources are properly cleaned up.
    
    Args:
        timeout_millis: Maximum time to wait for shutdown in milliseconds (default: 5000)
    """
    global _tracer_provider, _is_shutting_down
    
    if _tracer_provider:
        try:
            _is_shutting_down = True
            logger.info(f"Shutting down OpenTelemetry tracer provider (timeout: {timeout_millis}ms)")
            
            # Suppress OTLP exporter errors during shutdown
            import logging
            otlp_logger = logging.getLogger("opentelemetry.exporter.otlp.proto.grpc.exporter")
            original_level = otlp_logger.level
            otlp_logger.setLevel(logging.CRITICAL)
            
            try:
                # Try to flush with timeout, but don't block on failure
                try:
                    _tracer_provider.force_flush(timeout_millis=timeout_millis)
                except Exception as flush_error:
                    logger.debug(f"Error during tracer flush (continuing with shutdown): {flush_error}")
                
                # Shutdown with minimal blocking
                _tracer_provider.shutdown()
                logger.info("OpenTelemetry tracer provider shutdown completed")
            finally:
                # Restore original log level
                otlp_logger.setLevel(original_level)
        except Exception as e:
            logger.warning(f"Error during tracer shutdown: {e}")
        finally:
            _tracer_provider = None


# Global meter provider reference for proper shutdown
_meter_provider = None


def setup_metrics() -> None:
    """Configure OpenTelemetry metrics with OTLP exporter.
    
    Reads configuration from environment variables:
    - SERVICE_NAME: Name of the service (default: 'changeme')
    - SERVICE_VERSION: Version of the service (default: 'changeme')
    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (only used if OTEL_EXPORTER_OTLP_METRICS_ENDPOINT is not set)
    - OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: OTLP metrics endpoint (if not set, OTLP export is disabled)
    - OTEL_METRIC_EXPORT_INTERVAL: Export interval in milliseconds (default: 60000)
    - OTEL_METRIC_EXPORT_TIMEOUT: Export timeout in milliseconds (default: 5000)
    """
    global _meter_provider
    
    service_name = os.getenv("SERVICE_NAME", "changeme")
    service_version = os.getenv("SERVICE_VERSION", "changeme")
    resource = Resource.create(
        attributes={"service.name": service_name, "service.version": service_version}
    )

    # Check if OTLP export is enabled
    otlp_metrics_endpoint = os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    metric_readers = []
    
    if otlp_metrics_endpoint:
        logger.info(f"Configuring OTLP metric exporter with endpoint: {otlp_metrics_endpoint}")
        
        export_interval_millis = int(os.getenv("OTEL_METRIC_EXPORT_INTERVAL", "60000"))
        export_timeout_millis = int(os.getenv("OTEL_METRIC_EXPORT_TIMEOUT", "5000"))
        
        # Determine if endpoint is insecure (http vs https)
        insecure = otlp_metrics_endpoint.startswith("http://")
        
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=otlp_metrics_endpoint,
                timeout=export_timeout_millis // 1000,  # Convert to seconds
                insecure=insecure
            ),
            export_interval_millis=export_interval_millis,
            export_timeout_millis=export_timeout_millis
        )
        metric_readers.append(metric_reader)
    else:
        logger.info("OTLP metric export disabled (OTEL_EXPORTER_OTLP_METRICS_ENDPOINT not set)")
    
    _meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(_meter_provider)


def shutdown_metrics(timeout_millis: int = 5000) -> None:
    """Shutdown the metrics provider and flush pending metrics.
    
    This should be called during application shutdown to ensure all metrics
    are exported and resources are properly cleaned up.
    
    Args:
        timeout_millis: Maximum time to wait for shutdown in milliseconds (default: 5000)
    """
    global _meter_provider, _is_shutting_down
    
    if _meter_provider:
        try:
            _is_shutting_down = True
            logger.info(f"Shutting down OpenTelemetry metrics provider (timeout: {timeout_millis}ms)")
            
            # Suppress OTLP exporter errors during shutdown
            import logging
            otlp_logger = logging.getLogger("opentelemetry.exporter.otlp.proto.grpc.exporter")
            original_level = otlp_logger.level
            otlp_logger.setLevel(logging.CRITICAL)
            
            try:
                # Try to flush with timeout, but don't block on failure
                try:
                    _meter_provider.force_flush(timeout_millis=timeout_millis)
                except Exception as flush_error:
                    logger.debug(f"Error during metrics flush (continuing with shutdown): {flush_error}")
                
                # Shutdown with timeout
                _meter_provider.shutdown(timeout_millis=timeout_millis)
                logger.info("OpenTelemetry metrics provider shutdown completed")
            finally:
                # Restore original log level after a brief delay to catch straggler logs
                import time
                time.sleep(0.1)
                otlp_logger.setLevel(original_level)
        except Exception as e:
            logger.warning(f"Error during metrics shutdown: {e}")
        finally:
            _meter_provider = None


tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Create standard HTTP metrics
http_request_counter = meter.create_counter(
    name="http.server.request.count",
    description="Total number of HTTP requests",
    unit="1"
)

http_request_duration = meter.create_histogram(
    name="http.server.request.duration",
    description="HTTP request duration in milliseconds",
    unit="ms"
)

http_request_size = meter.create_histogram(
    name="http.server.request.size",
    description="HTTP request body size in bytes",
    unit="By"
)

http_response_size = meter.create_histogram(
    name="http.server.response.size",
    description="HTTP response body size in bytes",
    unit="By"
)

http_active_requests = meter.create_up_down_counter(
    name="http.server.active_requests",
    description="Number of active HTTP requests",
    unit="1"
)


async def trace_exceptions_middleware(request: Request, call_next: Callable):
    """Middleware to trace requests with distributed tracing.
    
    Note: Exception handling is delegated to global exception handlers
    to avoid redundancy and respect DEBUG settings.
    
    Args:
        request: Incoming FastAPI request
        call_next: Next middleware in the chain
        
    Returns:
        Response from the application
    """
    # Extract context from incoming headers
    carrier = dict(request.headers)
    ctx = extract(carrier)

    # Attach the extracted context to the current execution
    token = attach(ctx)

    try:
        with tracer.start_as_current_span(
            f"{request.method} {request.url.path}"
        ) as span:
            # Add user info from JWT
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                auth_token = auth_header.split(" ")[1]
                try:
                    payload = jwt.get_unverified_claims(auth_token)
                    if "preferred_username" in payload:
                        span.set_attribute("enduser.id", payload["preferred_username"])
                except JWTError:
                    pass  # Ignore invalid tokens

            response = await call_next(request)

            if response.status_code >= 400:
                span.set_status(
                    Status(StatusCode.ERROR, f"HTTP {response.status_code}")
                )

            return response
    except Exception as exc:
        # Record the exception in the span for tracing
        with tracer.start_as_current_span(
            f"{request.method} {request.url.path}"
        ) as span:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, f"An error occurred: {exc}"))
        
        # Re-raise to let global exception handlers handle it
        raise
    finally:
        detach(token)
