---
layout: default
title: Configuration
nav_order: 3
---

# Configuration Guide
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

All configuration is managed through environment variables. This allows for easy deployment across different environments without code changes.

## Application Settings

### Basic Configuration

```bash
# Application Identity
APP_TITLE=My API
APP_VERSION=1.0.0
DEBUG=False
LOG_LEVEL=INFO
```

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_TITLE` | "Change Title..." | Application name |
| `APP_VERSION` | "1.0" | Application version |
| `DEBUG` | False | Enable debug mode |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

## Middleware Configuration

### Enable/Disable Middleware

```bash
ENABLE_REQUEST_ID_MIDDLEWARE=True
ENABLE_SECURITY_HEADERS_MIDDLEWARE=True
ENABLE_LOGGING_MIDDLEWARE=True
ENABLE_ERROR_HANDLING_MIDDLEWARE=True
ENABLE_RATE_LIMIT_MIDDLEWARE=False
```

All middleware is enabled by default except rate limiting.

### Rate Limiting

```bash
ENABLE_RATE_LIMIT_MIDDLEWARE=True
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
```

| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_PER_MINUTE` | 60 | Requests per minute per client |
| `RATE_LIMIT_PER_HOUR` | 1000 | Requests per hour per client |

## OIDC/OAuth2 Configuration

### Discovery URL (Recommended)

```bash
OIDC_DISCOVERY_URL=https://auth.example.com/.well-known/openid-configuration
```

### Manual Configuration

```bash
OIDC_ISSUER=https://auth.example.com/realms/organization
OIDC_CLIENT_ID=my-client-id
OIDC_AUDIENCE=account
SWAGGER_CLIENT_ID=my-swagger-client-id
TOKEN_ALGORITHMS=RS256
```

### User Claims

```bash
OIDC_USER_NAME_CLAIM=preferred_username
OIDC_USER_ID_CLAIM=company
```

## CORS Configuration

```bash
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

Use `*` for development (not recommended in production):

```bash
ALLOWED_ORIGINS=*
```

## Database Configuration

### Connection Settings

```bash
DB_USER=postgres
DB_PASS=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb
DB_SCHEMA=public
```

### Connection Pool

```bash
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=3600
DB_POOL_TIMEOUT=30
ECHO_SQL=False
```

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_POOL_SIZE` | 5 | Number of connections to maintain |
| `DB_MAX_OVERFLOW` | 10 | Max connections beyond pool_size |
| `DB_POOL_RECYCLE` | 3600 | Recycle connections after N seconds |
| `DB_POOL_TIMEOUT` | 30 | Timeout for getting a connection |
| `ECHO_SQL` | False | Log all SQL statements |

### Initialization

```bash
INIT_DB=false  # Set to 'true' to drop and recreate tables (DANGEROUS!)
```

## OpenTelemetry Configuration

### Enable/Disable Instrumentation

```bash
# Enable/disable OpenTelemetry instrumentation (enabled by default)
ENABLE_OTEL_INSTRUMENTATION=True
```

When `ENABLE_OTEL_INSTRUMENTATION=True`, the FastAPI application created by `create_app()` is automatically instrumented with OpenTelemetry for distributed tracing.

### Service Identity

```bash
SERVICE_NAME=my-api
SERVICE_VERSION=1.0.0
```

### OTLP Exporter

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

Default endpoint connects to local Jaeger or OpenTelemetry Collector.

## Example .env File

See the complete example configuration:

```bash
# Application Configuration
APP_TITLE=My Production API
APP_VERSION=1.0.0
DEBUG=False
LOG_LEVEL=INFO

# OIDC Configuration
OIDC_DISCOVERY_URL=https://auth.example.com/.well-known/openid-configuration
OIDC_CLIENT_ID=my-client-id
OIDC_AUDIENCE=account
SWAGGER_CLIENT_ID=my-swagger-client-id
OIDC_USER_NAME_CLAIM=preferred_username
OIDC_USER_ID_CLAIM=sub

# CORS Configuration
ALLOWED_ORIGINS=https://myapp.example.com,https://admin.example.com
TOKEN_ALGORITHMS=RS256

# Database Configuration
DB_USER=postgres
DB_PASS=secure_password
DB_HOST=db.example.com
DB_PORT=5432
DB_NAME=production_db
DB_SCHEMA=public

# Database Connection Pool
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=3600
DB_POOL_TIMEOUT=30
ECHO_SQL=False

# Middleware Configuration
ENABLE_REQUEST_ID_MIDDLEWARE=True
ENABLE_SECURITY_HEADERS_MIDDLEWARE=True
ENABLE_LOGGING_MIDDLEWARE=True
ENABLE_ERROR_HANDLING_MIDDLEWARE=True
ENABLE_RATE_LIMIT_MIDDLEWARE=True

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=5000

# OpenTelemetry Configuration
ENABLE_OTEL_INSTRUMENTATION=True
SERVICE_NAME=my-production-api
SERVICE_VERSION=1.0.0
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

## Environment-Specific Configuration

### Development

```bash
DEBUG=True
LOG_LEVEL=DEBUG
ECHO_SQL=True
ALLOWED_ORIGINS=*
ENABLE_RATE_LIMIT_MIDDLEWARE=False
```

### Production

```bash
DEBUG=False
LOG_LEVEL=INFO
ECHO_SQL=False
ALLOWED_ORIGINS=https://yourdomain.com
ENABLE_RATE_LIMIT_MIDDLEWARE=True
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=5000
```

## Loading Configuration

The library automatically loads configuration from environment variables. You can use:

1. **System environment variables**
2. **.env file** (using python-dotenv)
3. **Container environment** (Docker, Kubernetes)

### Using .env file

```python
from dotenv import load_dotenv

load_dotenv()  # Load .env file

from fastapi_otel_common import create_app

app = create_app()
```

## Next Steps

- [Middleware Documentation](middleware) - Configure middleware
- [Security Guide](security) - Set up authentication
- [Database Guide](database) - Configure database
