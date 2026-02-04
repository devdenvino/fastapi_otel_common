---
layout: default
title: Middleware
nav_order: 4
---

# Middleware Documentation
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

This package includes production-ready middleware for FastAPI applications with security, logging, rate limiting, and error handling capabilities.

**All middleware components can be enabled/disabled and configured using environment variables.**

## Environment Variable Configuration

All middleware can be controlled via environment variables. See `env.example` for a complete configuration template.

### Middleware Enable/Disable Flags

```bash
# Enable/disable individual middleware (True/False)
ENABLE_REQUEST_ID_MIDDLEWARE=True
ENABLE_SECURITY_HEADERS_MIDDLEWARE=True
ENABLE_LOGGING_MIDDLEWARE=True
ENABLE_ERROR_HANDLING_MIDDLEWARE=True
ENABLE_RATE_LIMIT_MIDDLEWARE=False  # Disabled by default
```

### Rate Limiting Configuration

```bash
# Rate limiting settings (only applies if ENABLE_RATE_LIMIT_MIDDLEWARE=True)
RATE_LIMIT_PER_MINUTE=60           # Requests per minute per IP
RATE_LIMIT_PER_HOUR=1000           # Requests per hour per IP
```

Rate limiting is powered by [slowapi](https://github.com/laurentS/slowapi).

## Available Middleware

### 1. RequestIDMiddleware
Adds a unique request ID to each request for distributed tracing and debugging.

**Features:**
- Generates UUID v4 for each request
- Stores ID in `request.state.request_id`
- Adds `X-Request-ID` header to responses

**Usage:**
```python
from fastapi_otel_common.core import RequestIDMiddleware

app.add_middleware(RequestIDMiddleware)
```

### 2. SecurityHeadersMiddleware
Adds comprehensive security headers to all responses following OWASP best practices.

**Headers Added:**
- `X-Content-Type-Options`: Prevents MIME type sniffing
- `X-Frame-Options`: Prevents clickjacking
- `X-XSS-Protection`: Enables XSS filtering
- `Strict-Transport-Security`: Forces HTTPS
- `Content-Security-Policy`: Controls resource loading
- `Referrer-Policy`: Controls referrer information
- `Permissions-Policy`: Restricts browser features

**Usage:**
```python
from fastapi_otel_common.core import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)
```

### 3. LoggingMiddleware
Logs all requests and responses with timing information using **Loguru** and OpenTelemetry integration.

**Features:**
- **Loguru Integration**: High-performance logging with beautiful terminal formatting.
- **Automatic OTLP Export**: Logs are automatically forwarded to the configured OpenTelemetry backend.
- **Request/Response Details**: Method, path, client IP, and status codes.
- **Timing Info**: Precise request duration in milliseconds.
- **Correlation**: Automatic inclusion of Request ID and Trace/Span IDs for correlation.
- **Structured Errors**: Clear details for failed requests, including stack traces.

**Usage:**
```python
from fastapi_otel_common.core import LoggingMiddleware

app.add_middleware(LoggingMiddleware)
```

### 4. ErrorHandlingMiddleware
Global exception handler that catches unhandled exceptions and returns safe error responses.

**Features:**
- Catches all unhandled exceptions
- Logs full exception details
- Returns generic 500 error (doesn't leak internal details)
- Includes request ID in error response

**Usage:**
```python
from fastapi_otel_common.core import ErrorHandlingMiddleware

app.add_middleware(ErrorHandlingMiddleware)
```

### 5. Rate Limiting

**Features:**
- Global rate limiting per IP address
- Configurable per-minute and per-hour limits
- Redis backend support for distributed systems
- Automatic handling of rate limit exceeded responses
- Decorator support for per-route limits

**Default Limits:**
- 60 requests per minute per IP (configurable via `RATE_LIMIT_PER_MINUTE`)
- 1000 requests per hour per IP (configurable via `RATE_LIMIT_PER_HOUR`)

**Environment Variables:**
```bash
ENABLE_RATE_LIMIT_MIDDLEWARE=True     # Enable rate limiting
RATE_LIMIT_PER_MINUTE=60              # Requests per minute
RATE_LIMIT_PER_HOUR=1000              # Requests per hour
RATE_LIMITER_BACKEND=memory           # 'memory' (slowapi) or 'redis'
REDIS_URL=redis://localhost:6379      # Required if backend is 'redis'
```

**Global Rate Limiting:**
- **In-Memory (Default)**: When `RATE_LIMITER_BACKEND=memory`, rate limiting is powered by [slowapi](https://github.com/laurentS/slowapi) using its default in-memory storage. The limiter is accessible via `app.state.limiter`.
- **Distributed (Redis)**: When `RATE_LIMITER_BACKEND=redis`, a custom `RedisRateLimitMiddleware` is used to provide distributed rate limiting across multiple instances.

**Per-Route Rate Limiting (via slowapi):**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

@app.get("/api/expensive")
@limiter.limit("5/minute")  # Custom limit for this route
async def expensive_endpoint(request: Request):
    return {"status": "ok"}
```

**Redis Backend (for distributed systems):**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
import redis

# Configure Redis backend
redis_client = redis.from_url("redis://localhost:6379")
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)
```

slowapi supports Redis for distributed systems.

## Middleware Order

Middleware is executed in reverse order of how it's added. The recommended order is:

```python
from fastapi import FastAPI
from fastapi_otel_common.core import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    LoggingMiddleware,
    ErrorHandlingMiddleware,
)

app = FastAPI()

# Add in this order (last added executes first)
app.add_middleware(ErrorHandlingMiddleware)      # 1. Outermost - catches all errors
app.add_middleware(SecurityHeadersMiddleware)    # 2. Adds security headers
app.add_middleware(LoggingMiddleware)            # 3. Logs requests/responses
app.add_middleware(RequestIDMiddleware)          # 4. Innermost - adds request ID

# Rate limiting via slowapi (configured separately, not as middleware)
# Enabled via ENABLE_RATE_LIMIT_MIDDLEWARE=True
```

## Integration with create_app()

The `create_app()` function automatically includes all enabled middleware based on environment variables.

### Using Environment Variables (Recommended)

```bash
# Enable all middleware
export ENABLE_REQUEST_ID_MIDDLEWARE=True
export ENABLE_SECURITY_HEADERS_MIDDLEWARE=True
export ENABLE_LOGGING_MIDDLEWARE=True
export ENABLE_ERROR_HANDLING_MIDDLEWARE=True
export ENABLE_RATE_LIMIT_MIDDLEWARE=True

# Configure rate limiting
export RATE_LIMIT_PER_MINUTE=100
export RATE_LIMIT_PER_HOUR=5000
```

```python
from fastapi_otel_common import create_app

# Middleware automatically configured from environment variables
app = create_app(title="My API", version="1.0.0")
```

### Manual Configuration Override

You can still manually configure middleware after app creation if needed:

```python
# Uncomment this line to enable rate limiting
app.add_middleware(RateLimitMiddleware, requests_per_minute=60, requests_per_hour=1000)
```

## Customization

### Custom Rate Limits per Endpoint

For more granular control, you can use FastAPI dependencies:

```python
from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta
from collections import defaultdict

# Simple per-endpoint rate limiter
rate_limit_cache = defaultdict(list)

def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    def dependency(request: Request):
        client_ip = request.client.host
        now = datetime.now()
        cache_key = f"{client_ip}:{request.url.path}"
        
        # Clean old entries
        rate_limit_cache[cache_key] = [
            ts for ts in rate_limit_cache[cache_key]
            if (now - ts).total_seconds() < window_seconds
        ]
        
        # Check limit
        if len(rate_limit_cache[cache_key]) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        rate_limit_cache[cache_key].append(now)
    
    return dependency

# Use in route
@app.get("/api/expensive", dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60))])
async def expensive_endpoint():
    return {"status": "ok"}
```

## Production Considerations

1. **Rate Limiting:** The built-in rate limiter uses in-memory storage. For production:
   - Use Redis with libraries like `slowapi` or `fastapi-limiter`
   - Implement distributed rate limiting across multiple instances
   - Consider different limits for authenticated vs anonymous users

2. **Security Headers:** Review CSP policy based on your frontend requirements

3. **Logging:** Ensure OpenTelemetry is properly configured for your observability backend

4. **Error Handling:** Consider custom error handlers for specific exception types

## Example: Complete Setup

```python
from fastapi import FastAPI
from fastapi_otel_common import create_app
from fastapi_otel_common.core import RateLimitMiddleware

# Create app with all standard middleware and automatic OpenTelemetry instrumentation
app = create_app(
    title="My API",
    version="1.0.0"
)

# Optionally add rate limiting
# app.add_middleware(
#     RateLimitMiddleware,
#     requests_per_minute=100,
#     requests_per_hour=5000
# )

# Add your routes
@app.get("/")
async def root():
    return {"message": "Hello World"}
```

## Testing

To test middleware behavior:

```python
from fastapi.testclient import TestClient

def test_request_id_middleware():
    client = TestClient(app)
    response = client.get("/")
    assert "X-Request-ID" in response.headers
    
def test_security_headers():
    client = TestClient(app)
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"

def test_rate_limiting():
    client = TestClient(app)
    # Make requests up to limit
    for _ in range(60):
        response = client.get("/api/test")
        assert response.status_code == 200
    
    # Next request should be rate limited
    response = client.get("/api/test")
    assert response.status_code == 429
```
