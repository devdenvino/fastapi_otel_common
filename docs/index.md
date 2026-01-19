---
layout: default
title: Home
nav_order: 1
---

# FastAPI OTEL Common

Production-ready FastAPI components with OpenTelemetry integration and OIDC authentication.
{: .fs-6 .fw-300 }

[Get Started](#quick-start){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View on GitHub](https://github.com/devdenvino/fastapi_otel_common){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## Overview

`fastapi_otel_common` is a Python library designed to provide common utilities and components for FastAPI applications. It includes features such as configuration management, database integration, logging, routing, security, telemetry, and **production-ready middleware** for security, logging, rate limiting, and error handling.

## Key Features

- ✅ **Request ID Tracking** - Distributed tracing with unique request IDs
- ✅ **Security Headers** - OWASP-compliant security headers out of the box
- ✅ **OpenTelemetry Integration** - Full observability with distributed tracing
- ✅ **OIDC Authentication** - Production-ready OAuth2/OIDC integration
- ✅ **Rate Limiting** - Built-in rate limiting with slowapi
- ✅ **Structured Logging** - JSON-structured logs with correlation IDs
- ✅ **Database Management** - Async SQLAlchemy with connection pooling
- ✅ **Type Safe** - Full type hints and PEP 561 compliance

## Quick Start

### Installation

```bash
pip install fastapi_otel_common
```

### Basic Usage

```python
from fastapi_otel_common import create_app, instrument_app

# Create app with built-in middleware
app = create_app(
    title="My API",
    version="1.0.0"
)

# Instrument for OpenTelemetry
instrument_app(app)

@app.get("/")
async def root():
    return {"message": "Hello World"}
```

### Environment Configuration

Create a `.env` file:

```bash
# Application
APP_TITLE=My API
APP_VERSION=1.0.0
DEBUG=False

# Middleware
ENABLE_REQUEST_ID_MIDDLEWARE=True
ENABLE_SECURITY_HEADERS_MIDDLEWARE=True
ENABLE_LOGGING_MIDDLEWARE=True
ENABLE_ERROR_HANDLING_MIDDLEWARE=True
ENABLE_RATE_LIMIT_MIDDLEWARE=True

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# OpenTelemetry
SERVICE_NAME=my-api
SERVICE_VERSION=1.0.0
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## What's Next?

- [Installation Guide](installation.md) - Detailed installation instructions
- [Configuration](configuration.md) - Complete configuration reference
- [Middleware](middleware.md) - Middleware documentation
- [Security](security.md) - Authentication and authorization
- [Database](database.md) - Database integration guide
- [Examples](examples.md) - Full working examples

## Requirements

- Python 3.12+
- FastAPI 0.116.1+
- OpenTelemetry SDK 1.36.0+

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/devdenvino/fastapi_otel_common/blob/main/LICENSE) file for details.
