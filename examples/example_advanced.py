"""
Example demonstrating the new features in fastapi_otel_common v0.1.0

This example shows:
1. OpenTelemetry Metrics collection
2. Advanced health checks
3. Redis rate limiting (optional)
4. Lifecycle management
"""
import os
from fastapi import FastAPI, Depends
from fastapi_otel_common import create_app
from fastapi_otel_common.security import get_current_user
from fastapi_otel_common.core.models import UserBase

# Configure environment
os.environ.update({
    # Application
    "APP_TITLE": "Advanced API Example",
    "APP_VERSION": "1.0.0",
    "DEBUG": "False",
    
    # OpenTelemetry
    "SERVICE_NAME": "advanced-api",
    "SERVICE_VERSION": "1.0.0",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
    
    # Enable metrics
    "ENABLE_OTEL_METRICS": "True",
    "OTEL_METRIC_EXPORT_INTERVAL": "60000",
    
    # Rate limiting (choose backend)
    "ENABLE_RATE_LIMIT_MIDDLEWARE": "True",
    "RATE_LIMITER_BACKEND": "memory",  # Change to 'redis' for production
    # "REDIS_URL": "redis://localhost:6379",  # Uncomment for Redis backend
    "RATE_LIMIT_PER_MINUTE": "60",
    "RATE_LIMIT_PER_HOUR": "1000",
    
    # Middleware
    "ENABLE_REQUEST_ID_MIDDLEWARE": "True",
    "ENABLE_SECURITY_HEADERS_MIDDLEWARE": "True",
    "ENABLE_LOGGING_MIDDLEWARE": "True",
})

# Create app with all features enabled
app = create_app(
    title="Advanced API Example",
    version="1.0.0",
    description="Demonstrates fastapi_otel_common v0.1.0 features"
)


@app.get("/")
async def root():
    """
    Simple root endpoint.
    
    Automatically tracked with:
    - OpenTelemetry tracing
    - OpenTelemetry metrics
    - Request logging
    - Rate limiting
    """
    return {
        "message": "Welcome to Advanced API",
        "features": [
            "OpenTelemetry Metrics",
            "Health Checks (/healthz, /readyz, /livez)",
            "Rate Limiting",
            "Security Headers",
            "Request Tracking"
        ]
    }


@app.get("/api/data")
async def get_data():
    """
    Example API endpoint.
    
    Metrics collected:
    - http.server.request.count
    - http.server.request.duration
    - http.server.active_requests
    """
    return {
        "data": [1, 2, 3, 4, 5],
        "timestamp": "2026-01-20T10:30:00Z"
    }


@app.post("/api/data")
async def create_data(item: dict):
    """
    Example POST endpoint.
    
    Metrics include request and response sizes.
    """
    return {
        "id": "12345",
        "created": True,
        "item": item
    }


@app.get("/protected")
async def protected_endpoint(user: UserBase = Depends(get_current_user)):
    """
    Protected endpoint requiring OIDC authentication.
    
    User information is automatically added to OpenTelemetry spans.
    """
    return {
        "message": f"Hello, {user.username}!",
        "user_id": user.id,
        "email": user.email
    }


@app.get("/metrics-demo")
async def metrics_demo():
    """
    Endpoint to demonstrate custom metrics.
    
    Use the meter from telemetry.tracing to create custom metrics.
    """
    from fastapi_otel_common.telemetry.tracing import meter
    
    # Create a custom counter
    demo_counter = meter.create_counter(
        name="demo.custom.counter",
        description="Example custom counter",
        unit="1"
    )
    
    # Increment it
    demo_counter.add(1, {"endpoint": "metrics-demo"})
    
    return {
        "message": "Custom metric recorded",
        "metric": "demo.custom.counter"
    }


# Health check endpoints are automatically included:
# - GET /healthz   - Liveness probe
# - GET /livez     - Liveness probe (alias)
# - GET /readyz    - Readiness probe (checks DB and OIDC)
# - GET /startupz  - Startup probe


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("FastAPI OTEL Common v0.1.0 - Advanced Features Demo")
    print("=" * 60)
    print("\n🚀 Starting application with:")
    print("  ✅ OpenTelemetry Tracing")
    print("  ✅ OpenTelemetry Metrics")
    print("  ✅ Health Checks")
    print("  ✅ Rate Limiting")
    print("  ✅ Security Headers")
    print("  ✅ Request Logging")
    print("\n📊 Available endpoints:")
    print("  - http://localhost:8000/          - Root endpoint")
    print("  - http://localhost:8000/docs      - Swagger UI")
    print("  - http://localhost:8000/healthz   - Liveness probe")
    print("  - http://localhost:8000/readyz    - Readiness probe")
    print("  - http://localhost:8000/livez     - Liveness probe")
    print("  - http://localhost:8000/startupz  - Startup probe")
    print("\n📈 Metrics exported to: http://localhost:4317 (OTLP)")
    print("=" * 60)
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
