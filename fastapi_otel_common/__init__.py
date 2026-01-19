"""
FastAPI OTEL Common - Production-ready FastAPI components with OpenTelemetry integration.

This package provides:
- FastAPI application factory with built-in middleware
- OpenTelemetry instrumentation
- Request ID tracking for distributed tracing
- Security headers (OWASP best practices)
- Request/response logging with timing
- Global error handling
- Rate limiting protection (powered by slowapi)
"""
from .app import create_app, instrument_app
from .core.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)

__version__ = "0.0.2"

__all__ = [
    "create_app",
    "instrument_app",
    "ErrorHandlingMiddleware",
    "LoggingMiddleware",
    "RateLimitMiddleware",
    "RequestIDMiddleware",
    "SecurityHeadersMiddleware",
]
