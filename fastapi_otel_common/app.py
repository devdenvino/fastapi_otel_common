import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.cors import CORSMiddleware

from .core.config import (
    ALLOWED_ORIGINS,
    APP_TITLE,
    APP_VERSION,
    DEBUG,
    ENABLE_LOGGING_MIDDLEWARE,
    ENABLE_OTEL_INSTRUMENTATION,
    ENABLE_OTEL_METRICS,
    ENABLE_RATE_LIMIT_MIDDLEWARE,
    ENABLE_REQUEST_ID_MIDDLEWARE,
    ENABLE_SECURITY_HEADERS_MIDDLEWARE,
    RATE_LIMIT_PER_HOUR,
    RATE_LIMIT_PER_MINUTE,
    RATE_LIMITER_BACKEND,
    REDIS_URL,
    SWAGGER_CLIENT_ID,
)
from .core.middleware import (
    LoggingMiddleware,
    MetricsMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from .logging.logger import get_logger
from .routes import health
from .telemetry.tracing import setup_tracer, setup_metrics, trace_exceptions_middleware

logger = get_logger(__name__)

# Global Redis rate limiter instance
_redis_rate_limiter: Optional[Any] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifecycle with proper startup and shutdown.
    
    Startup:
    - Initialize Redis rate limiter (if configured)
    - Mark startup as complete for health checks
    
    Shutdown:
    - Close Redis connections
    - Cleanup resources
    
    Args:
        app: FastAPI application instance
        
    Yields:
        None
    """
    global _redis_rate_limiter
    
    # Startup
    logger.info("Application startup initiated")
    
    try:
        # Initialize Redis rate limiter if configured
        if ENABLE_RATE_LIMIT_MIDDLEWARE and RATE_LIMITER_BACKEND == "redis":
            from .ratelimit.redis import RedisRateLimiter
            
            _redis_rate_limiter = RedisRateLimiter(
                redis_url=REDIS_URL,
                per_minute=RATE_LIMIT_PER_MINUTE,
                per_hour=RATE_LIMIT_PER_HOUR,
            )
            await _redis_rate_limiter.connect()
            logger.info("Redis rate limiter initialized")
        
        # Mark startup as complete for health checks
        health.mark_startup_complete()
        logger.info("Application startup completed successfully")
        
        yield
        
    finally:
        # Shutdown
        logger.info("Application shutdown initiated")
        
        # Suppress OTLP exporter errors during shutdown to avoid confusing error messages
        import logging
        otlp_logger = logging.getLogger("opentelemetry.exporter.otlp.proto.grpc.exporter")
        otlp_logger.setLevel(logging.CRITICAL)
        
        # Cleanup Redis connection
        if _redis_rate_limiter:
            await _redis_rate_limiter.disconnect()
            logger.info("Redis rate limiter disconnected")
        
        # Shutdown OpenTelemetry metrics with timeout
        if ENABLE_OTEL_METRICS:
            from .telemetry.tracing import shutdown_metrics
            shutdown_timeout = int(os.getenv("OTEL_SHUTDOWN_TIMEOUT", "3000"))
            shutdown_metrics(timeout_millis=shutdown_timeout)
        
        # Shutdown OpenTelemetry tracer with timeout
        if ENABLE_OTEL_INSTRUMENTATION:
            from .telemetry.tracing import shutdown_tracer
            shutdown_timeout = int(os.getenv("OTEL_SHUTDOWN_TIMEOUT", "3000"))
            shutdown_tracer(timeout_millis=shutdown_timeout)
        
        # Brief sleep to allow background exporter threads to finish
        import asyncio
        import time
        time.sleep(0.2)
        
        logger.info("Application shutdown completed")


def _get_default_config(**kwargs: Any) -> dict[str, Any]:
    """Get default FastAPI configuration with merged user overrides.
    
    Args:
        **kwargs: User-provided configuration overrides
        
    Returns:
        Merged configuration dictionary
    """
    defaults = {
        "title": APP_TITLE + ' API',
        "version": APP_VERSION,
        "swagger_ui_oauth2_redirect_url": "/docs/oauth2-redirect",
        "swagger_ui_init_oauth": {
            "usePkceWithAuthorizationCodeGrant": True,
            "useBasicAuthenticationWithAccessCodeGrant": False,
            "clientId": SWAGGER_CLIENT_ID or "",
            "scopes": "openid profile email api:read api:write",
        },
        "swagger_ui_parameters": {
            "oauth2RedirectUrl": "/docs/oauth2-redirect",
        },
    }
    
    # Merge swagger_ui_init_oauth if provided
    if "swagger_ui_init_oauth" in kwargs and isinstance(kwargs["swagger_ui_init_oauth"], dict):
        merged_oauth = defaults["swagger_ui_init_oauth"].copy()
        merged_oauth.update(kwargs["swagger_ui_init_oauth"])
        kwargs["swagger_ui_init_oauth"] = merged_oauth
    
    # Merge swagger_ui_parameters if provided
    if "swagger_ui_parameters" in kwargs and isinstance(kwargs["swagger_ui_parameters"], dict):
        merged_params = defaults["swagger_ui_parameters"].copy()
        merged_params.update(kwargs["swagger_ui_parameters"])
        kwargs["swagger_ui_parameters"] = merged_params
    
    # Apply defaults for any missing keys
    for key, value in defaults.items():
        kwargs.setdefault(key, value)
    
    return kwargs


def _setup_rate_limiting(app: FastAPI) -> None:
    """Configure rate limiting for the application.
    
    Args:
        app: FastAPI application instance
    """
    if ENABLE_RATE_LIMIT_MIDDLEWARE:
        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=[f"{RATE_LIMIT_PER_MINUTE}/minute", f"{RATE_LIMIT_PER_HOUR}/hour"]
        )
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _setup_middleware(app: FastAPI) -> None:
    """Configure all middleware in the correct order.
    
    Middleware is added in reverse order (last added is executed first).
    All middleware can be enabled/disabled via environment variables.
    
    Args:
        app: FastAPI application instance
    """
    global _redis_rate_limiter
    
    # 1. Security headers (outermost)
    if ENABLE_SECURITY_HEADERS_MIDDLEWARE:
        app.add_middleware(SecurityHeadersMiddleware)
    
    # 2. Redis rate limiting (if configured)
    if ENABLE_RATE_LIMIT_MIDDLEWARE and RATE_LIMITER_BACKEND == "redis" and _redis_rate_limiter:
        from .ratelimit.redis import RedisRateLimitMiddleware
        app.add_middleware(RedisRateLimitMiddleware, limiter=_redis_rate_limiter)
        logger.info("Redis rate limiting middleware added")
    
    # 3. Metrics collection (after rate limiting)
    if ENABLE_OTEL_METRICS:
        app.add_middleware(MetricsMiddleware)
    
    # 4. Logging (logs after metrics are recorded)
    if ENABLE_LOGGING_MIDDLEWARE:
        app.add_middleware(LoggingMiddleware)
    
    # 5. Request ID (innermost - adds ID for all downstream processing)
    if ENABLE_REQUEST_ID_MIDDLEWARE:
        app.add_middleware(RequestIDMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Tracing middleware
    app.middleware("http")(trace_exceptions_middleware)


def _setup_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers.
    
    Args:
        app: FastAPI application instance
    """
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle validation errors with detailed error messages."""
        logger.error(
            f"Validation error on {request.method} {request.url.path}: {exc.errors()}"
        )
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Validation error",
                "errors": exc.errors(),
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all unhandled exceptions globally."""
        logger.exception(
            f"Unhandled exception: {str(exc)}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "request_id": getattr(request.state, "request_id", None)
            }
        )
        
        # In production, don't leak error details
        detail = str(exc) if DEBUG else "An internal error occurred. Please try again later."
        
        return JSONResponse(
            status_code=500,
            content={
                "detail": detail,
                "request_id": getattr(request.state, "request_id", None)
            }
        )


def create_app(**kwargs: Any) -> FastAPI:
    """Create and configure a FastAPI application with telemetry and middleware.
    
    Args:
        **kwargs: Additional configuration options passed to FastAPI constructor.
                 Set lifespan=None to disable the default lifespan manager.
        
    Returns:
        Configured FastAPI application instance
    """
    setup_tracer()
    
    # Initialize metrics if enabled
    if ENABLE_OTEL_METRICS:
        setup_metrics()
    
    # Get merged configuration
    config = _get_default_config(**kwargs)
    
    # Add lifespan if not explicitly disabled
    if "lifespan" not in kwargs:
        config["lifespan"] = lifespan
    
    app = FastAPI(**config)

    # Setup components in order
    _setup_instrumentation(app)  # Must be first to capture full request time
    _setup_rate_limiting(app)
    _setup_middleware(app)
    _setup_exception_handlers(app)
    
    # Include routers
    app.include_router(health.router)

    return app

    # Setup components in order
    _setup_instrumentation(app)  # Must be first to capture full request time
    _setup_rate_limiting(app)
    _setup_middleware(app)
    _setup_exception_handlers(app)
    
    # Include routers
    app.include_router(health.router)

    return app


def _setup_instrumentation(app: FastAPI) -> None:
    """Instrument FastAPI application with OpenTelemetry.
    
    Args:
        app: FastAPI application instance to instrument
    """
    if ENABLE_OTEL_INSTRUMENTATION:
        FastAPIInstrumentor.instrument_app(app)
