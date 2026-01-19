from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

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
    ENABLE_ERROR_HANDLING_MIDDLEWARE,
    ENABLE_LOGGING_MIDDLEWARE,
    ENABLE_RATE_LIMIT_MIDDLEWARE,
    ENABLE_REQUEST_ID_MIDDLEWARE,
    ENABLE_SECURITY_HEADERS_MIDDLEWARE,
    RATE_LIMIT_PER_HOUR,
    RATE_LIMIT_PER_MINUTE,
    SWAGGER_CLIENT_ID,
)
from .core.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)
from .logging.logger import get_logger
from .routes import health
from .telemetry.tracing import setup_tracer, trace_exceptions_middleware

logger = get_logger(__name__)


def create_app(**kwargs: Any) -> FastAPI:
    setup_tracer()

    # Set default values for key parameters
    defaults = {
        "title": APP_TITLE + ' API',
        "version": APP_VERSION,
        "swagger_ui_oauth2_redirect_url": "/docs/oauth2-redirect",
        "swagger_ui_init_oauth": {
            "usePkceWithAuthorizationCodeGrant": True,
            "clientId": SWAGGER_CLIENT_ID or "",
            "scopes": "openid profile email api:read api:write",
        },
    }
    
    # Merge swagger_ui_init_oauth if provided
    if "swagger_ui_init_oauth" in kwargs and isinstance(kwargs["swagger_ui_init_oauth"], dict):
        merged_oauth = defaults["swagger_ui_init_oauth"].copy()
        merged_oauth.update(kwargs["swagger_ui_init_oauth"])
        kwargs["swagger_ui_init_oauth"] = merged_oauth
    
    # Apply defaults for any missing keys
    for key, value in defaults.items():
        kwargs.setdefault(key, value)

    app = FastAPI(**kwargs)

    # Instrument the app FIRST to capture the full request time, including other middleware.
    instrument_app(app)

    # Initialize rate limiter using slowapi
    if ENABLE_RATE_LIMIT_MIDDLEWARE:
        limiter = Limiter(
            key_func=get_remote_address,
            default_limits=[f"{RATE_LIMIT_PER_MINUTE}/minute", f"{RATE_LIMIT_PER_HOUR}/hour"]
        )
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add middleware in order (last added is executed first)
    # All middleware can be enabled/disabled via environment variables
    
    # 1. Error handling (outermost - catches all errors)
    if ENABLE_ERROR_HANDLING_MIDDLEWARE:
        app.add_middleware(ErrorHandlingMiddleware)
    
    # 2. Security headers
    if ENABLE_SECURITY_HEADERS_MIDDLEWARE:
        app.add_middleware(SecurityHeadersMiddleware)
    
    # 3. Logging (logs after security headers are added)
    if ENABLE_LOGGING_MIDDLEWARE:
        app.add_middleware(LoggingMiddleware)
    
    # 4. Request ID (innermost - adds ID for all downstream processing)
    if ENABLE_REQUEST_ID_MIDDLEWARE:
        app.add_middleware(RequestIDMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.middleware("http")(trace_exceptions_middleware)

    # Exception handlers
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

    app.include_router(health.router)

    return app


def instrument_app(app: FastAPI) -> None:
    """Instrument FastAPI application with OpenTelemetry.
    
    Args:
        app: FastAPI application instance to instrument
    """
    FastAPIInstrumentor.instrument_app(app)
