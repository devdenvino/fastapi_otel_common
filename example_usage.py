"""Example usage of fastapi_otel_common middleware.

Demonstrates two approaches:
1. Using create_app() with automatic middleware configuration
2. Manual middleware setup for fine-grained control
"""
from fastapi import FastAPI

from fastapi_otel_common import (
    RateLimitMiddleware,
    create_app,
)

# Option 1: Use create_app with built-in middleware (RECOMMENDED)
# All middleware is configured via environment variables
# OpenTelemetry instrumentation is automatic when enabled via ENABLE_OTEL_INSTRUMENTATION=True
# See env.example for available configuration options
app = create_app(
    title="My API",
    version="1.0.0",
    description="API with OpenTelemetry and security middleware"
)

# Optionally add rate limiting (commented out by default)
# Uncomment to enable rate limiting with custom settings
# app.add_middleware(
#     RateLimitMiddleware,
#     requests_per_minute=100,
#     requests_per_hour=5000,
#     cleanup_interval=300
# )


# Option 2: Manual setup with individual middleware (for advanced use cases)
"""
from fastapi import FastAPI
from fastapi_otel_common import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)

app = FastAPI(title="My API", version="1.0.0")

# Add middleware in reverse order (last added executes first)
app.add_middleware(ErrorHandlingMiddleware)      # Outermost: catches all errors
app.add_middleware(SecurityHeadersMiddleware)    # Adds security headers
app.add_middleware(LoggingMiddleware)            # Logs requests/responses
app.add_middleware(RateLimitMiddleware,          # Rate limiting (optional)
                   requests_per_minute=100,
                   requests_per_hour=5000)
app.add_middleware(RequestIDMiddleware)          # Innermost: adds request ID
"""


# Add your routes
@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {"message": "Hello World", "status": "ok"}


@app.get("/api/data")
async def get_data() -> dict:
    """Example API endpoint with sample data."""
    return {
        "data": [1, 2, 3, 4, 5],
        "count": 5
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
