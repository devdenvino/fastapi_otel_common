from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.propagate import extract
from opentelemetry.context import attach, detach
from fastapi import Request

import traceback
from fastapi.responses import JSONResponse
from jose import jwt, JWTError

import os

from ..logging.logger import get_logger

logger = get_logger(__name__)


def setup_tracer():
    service_name = os.getenv("SERVICE_NAME", "changeme")
    service_version = os.getenv("SERVICE_VERSION", "changeme")
    resource = Resource.create(
        attributes={"service.name": service_name, "service.version": service_version}
    )

    provider = TracerProvider(resource=resource)
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
    provider.add_span_processor(processor)# Instrument the Python logging module to automatically add trace IDs
    # This is the key step to link your logs to your traces.
    trace.set_tracer_provider(provider)


tracer = trace.get_tracer(__name__)


async def trace_exceptions_middleware(request: Request, call_next):
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
        # Extract traceback and exception type
        exc_type = type(exc).__name__
        exc_traceback = traceback.format_exc()

        
        logger.error(f"An error occurred: {exc}")
        logger.error(traceback.format_exc())

        # Record the exception in the span
        with tracer.start_as_current_span(
            f"{request.method} {request.url.path}"
        ) as span:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, f"An error occurred: {exc}"))


        # Return detailed error response
        return JSONResponse(
            status_code=500,
            content={
                "message": "Internal Server Error",
                "error_type": exc_type,
                "error_message": str(exc),
                "traceback": exc_traceback,
            },
        )
    finally:
        detach(token)
