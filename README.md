# FastAPI OTEL Common

[![PyPI version](https://badge.fury.io/py/fastapi-otel-common.svg)](https://badge.fury.io/py/fastapi-otel-common)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://devdenvino.github.io/fastapi_otel_common/)

Production-ready FastAPI components with OpenTelemetry integration, OIDC authentication, and enterprise features.

## 🚀 Features

### Observability
- ✅ **OpenTelemetry Tracing** - Full distributed tracing with OTLP export
- ✅ **OpenTelemetry Metrics** - HTTP request metrics (count, duration, size)
- ✅ **Structured Logging** - JSON-structured logs with correlation IDs
- ✅ **Request ID Tracking** - Distributed tracing with unique request IDs

### Security & Authentication
- ✅ **OIDC Authentication** - Production-ready OAuth2/OIDC integration
- ✅ **Role-Based Access Control (RBAC)** - Client-specific role checking
- ✅ **Security Headers** - OWASP-compliant security headers out of the box
- ✅ **Rate Limiting** - Memory or Redis-backed rate limiting

### Reliability
- ✅ **Health Checks** - Kubernetes-compatible liveness/readiness/startup probes
- ✅ **Lifecycle Management** - Proper startup/shutdown with resource cleanup
- ✅ **Database Management** - Async SQLAlchemy with connection pooling

### Developer Experience
- ✅ **Type Safe** - Full type hints and PEP 561 compliance
- ✅ **Environment-Driven Config** - Zero-config with sensible defaults
- ✅ **One-Line Setup** - Get started with a single function call

## 📦 Installation

```bash
# Basic installation
pip install fastapi_otel_common

# With Redis support for distributed rate limiting
pip install fastapi_otel_common[redis]
```

## 🏃 Quick Start

```python
from fastapi_otel_common import create_app

# Create app with built-in middleware and OpenTelemetry instrumentation
app = create_app(
    title="My API",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

# That's it! Your app now has:
# ✅ OpenTelemetry tracing and metrics
# ✅ Security headers
# ✅ Health check endpoints (/healthz, /readyz, /livez)
# ✅ Request logging
# ✅ Structured error handling
```

## 📚 Documentation

Full documentation is available at: **https://devdenvino.github.io/fastapi_otel_common/**

- [Installation Guide](https://devdenvino.github.io/fastapi_otel_common/installation.html)
- [Configuration](https://devdenvino.github.io/fastapi_otel_common/configuration.html)
- [Middleware](https://devdenvino.github.io/fastapi_otel_common/middleware.html)
- [OpenTelemetry Metrics](docs/metrics.md)
- [Health Checks](docs/health-checks.md)
- [Rate Limiting](docs/rate-limiting.md)
- [Role-Based Access Control](docs/role-based-access-control.md)
- [Security](https://devdenvino.github.io/fastapi_otel_common/security.html)
- [Database](https://devdenvino.github.io/fastapi_otel_common/database.html)
- [Examples](https://devdenvino.github.io/fastapi_otel_common/examples.html)
- [Contributing](https://devdenvino.github.io/fastapi_otel_common/contributing.html)

## 🔧 Configuration

Configure via environment variables:

```bash
# Application
APP_TITLE=My API
APP_VERSION=1.0.0
DEBUG=False

# Middleware
ENABLE_REQUEST_ID_MIDDLEWARE=True
ENABLE_SECURITY_HEADERS_MIDDLEWARE=True
ENABLE_LOGGING_MIDDLEWARE=True
ENABLE_RATE_LIMIT_MIDDLEWARE=False

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
RATE_LIMITER_BACKEND=memory  # or 'redis' for distributed
REDIS_URL=redis://localhost:6379

# OpenTelemetry
SERVICE_NAME=my-api
SERVICE_VERSION=1.0.0
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
ENABLE_OTEL_INSTRUMENTATION=True
ENABLE_OTEL_METRICS=True
OTEL_METRIC_EXPORT_INTERVAL=60000  # Export interval in milliseconds
OTEL_METRIC_EXPORT_TIMEOUT=5000    # Export timeout in milliseconds (prevents shutdown hangs)
```

## 🏥 Health Checks

Kubernetes-compatible health probes are automatically included:

```python
# GET /healthz  - Liveness probe
# GET /livez    - Liveness probe (alias)
# GET /readyz   - Readiness probe (checks DB and OIDC)
# GET /startupz - Startup probe
```

Example Kubernetes configuration:

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /readyz
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

See [Health Checks Documentation](docs/health-checks.md) for details.

## 🛡️ Security

Includes production-ready security features:

### Basic Authentication

```python
from fastapi import Depends
from fastapi_otel_common import create_app
from fastapi_otel_common.security import get_current_user
from fastapi_otel_common.core.models import UserBase

app = create_app()

@app.get("/protected")
async def protected_route(user: UserBase = Depends(get_current_user)):
    return {"user_id": user.id, "email": user.email}
```

### Role-Based Access Control (RBAC)

Protect endpoints with client-specific role requirements:

```python
from fastapi_otel_common.security import RequireRoles

# Require admin or manager role for my-client-id
@app.get("/admin/dashboard")
async def admin_dashboard(
    user: UserBase = Depends(RequireRoles("my-client-id", ["admin", "manager"]))
):
    return {"message": f"Welcome {user.given_name}", "roles": user.roles}

# Use as dependency without accessing user
@app.delete(
    "/admin/system",
    dependencies=[Depends(RequireRoles("my-client-id", ["super-admin"]))]
)
async def dangerous_operation():
    return {"message": "Operation completed"}
```

See [Role-Based Access Control Documentation](docs/role-based-access-control.md) for details.

## 💾 Database

Async SQLAlchemy with **multi-database support** via adapter pattern:

### Quick Start with SQLite (Development)

```bash
# No PostgreSQL needed! Just set DB_TYPE
DB_TYPE=sqlite
SQLITE_DB_PATH=./data/app.db
```

### Production with PostgreSQL

```bash
DB_TYPE=postgresql
DB_USER=postgres
DB_PASS=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb
```

### Using in FastAPI

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_otel_common.database import get_db_session

@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(User))
    return result.scalars().all()
```

## 📊 Observability

Full OpenTelemetry integration for distributed tracing and metrics:

### Tracing
- Automatic request tracing
- Database query tracing
- Custom span creation
- Context propagation
- OTLP/Jaeger export

### Metrics
Automatically collected HTTP metrics:
- **Request count** by method, path, and status code
- **Request duration** histogram in milliseconds
- **Request/response sizes** histograms
- **Active requests** counter

```python
# Metrics are automatically exported to your OTLP collector
# View in Grafana, Prometheus, or any OpenTelemetry-compatible backend
```

See [Metrics Documentation](docs/metrics.md) for visualization and querying.

## 🧪 Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest --cov=fastapi_otel_common

# Format code
black .

# Lint
ruff check .

# Type check
mypy fastapi_otel_common
```

## 🤝 Contributing

Contributions are welcome! Please see our [Contributing Guide](https://devdenvino.github.io/fastapi_otel_common/contributing.html) for details.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- FastAPI team for the amazing framework
- OpenTelemetry community for observability tools
- slowapi for rate limiting

## 📧 Support

- 📖 [Documentation](https://devdenvino.github.io/fastapi_otel_common/)
- 🐛 [Issue Tracker](https://github.com/devdenvino/fastapi_otel_common/issues)
- 💬 [Discussions](https://github.com/devdenvino/fastapi_otel_common/discussions)
