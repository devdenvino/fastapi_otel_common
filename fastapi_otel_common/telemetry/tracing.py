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


def setup_tracer() -> None:
    """Configure OpenTelemetry tracer with OTLP exporter.
    
    Reads configuration from environment variables:
    - SERVICE_NAME: Name of the service (default: 'changeme')
    - SERVICE_VERSION: Version of the service (default: 'changeme')
    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (default: 'http://localhost:4317')
    """
    global _tracer_provider
    
    service_name = os.getenv("SERVICE_NAME", "changeme")
    service_version = os.getenv("SERVICE_VERSION", "changeme")
    resource = Resource.create(
        attributes={"service.name": service_name, "service.version": service_version}
    )

    _tracer_provider = TracerProvider(resource=resource)
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
    _tracer_provider.add_span_processor(processor)
    
    trace.set_tracer_provider(_tracer_provider)


def shutdown_tracer() -> None:
    """Shutdown the tracer provider and flush pending spans.
    
    This should be called during application shutdown to ensure all spans
    are exported and resources are properly cleaned up.
    """
    global _tracer_provider
    
    if _tracer_provider:
        try:
            logger.info("Shutting down OpenTelemetry tracer provider")
            _tracer_provider.shutdown()
            logger.info("OpenTelemetry tracer provider shutdown completed")
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
    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (default: 'http://localhost:4317')
    - OTEL_METRIC_EXPORT_INTERVAL: Export interval in milliseconds (default: 60000)
    - OTEL_METRIC_EXPORT_TIMEOUT: Export timeout in milliseconds (default: 5000)
    """
    global _meter_provider
    
    service_name = os.getenv("SERVICE_NAME", "changeme")
    service_version = os.getenv("SERVICE_VERSION", "changeme")
    resource = Resource.create(
        attributes={"service.name": service_name, "service.version": service_version}
    )

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    export_interval_millis = int(os.getenv("OTEL_METRIC_EXPORT_INTERVAL", "60000"))
    export_timeout_millis = int(os.getenv("OTEL_METRIC_EXPORT_TIMEOUT", "5000"))
    
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(
            endpoint=otlp_endpoint,
            timeout=export_timeout_millis // 1000  # Convert to seconds
        ),
        export_interval_millis=export_interval_millis
    )
    
    _meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(_meter_provider)


def shutdown_metrics() -> None:
    """Shutdown the metrics provider and flush pending metrics.
    
    This should be called during application shutdown to ensure all metrics
    are exported and resources are properly cleaned up.
    """
    global _meter_provider
    
    if _meter_provider:
        try:
            logger.info("Shutting down OpenTelemetry metrics provider")
            _meter_provider.shutdown()
            logger.info("OpenTelemetry metrics provider shutdown completed")
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
