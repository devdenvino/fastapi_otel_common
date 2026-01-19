# FastAPI OTEL Common

[![PyPI version](https://badge.fury.io/py/fastapi-otel-common.svg)](https://badge.fury.io/py/fastapi-otel-common)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://devdenvino.github.io/fastapi_otel_common/)

Production-ready FastAPI components with OpenTelemetry integration and OIDC authentication.

## 🚀 Features

- ✅ **Request ID Tracking** - Distributed tracing with unique request IDs
- ✅ **Security Headers** - OWASP-compliant security headers out of the box
- ✅ **OpenTelemetry Integration** - Full observability with distributed tracing
- ✅ **OIDC Authentication** - Production-ready OAuth2/OIDC integration
- ✅ **Rate Limiting** - Built-in rate limiting with slowapi
- ✅ **Structured Logging** - JSON-structured logs with correlation IDs
- ✅ **Database Management** - Async SQLAlchemy with connection pooling
- ✅ **Type Safe** - Full type hints and PEP 561 compliance

## 📦 Installation

```bash
pip install fastapi_otel_common
```

## 🏃 Quick Start

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

## 📚 Documentation

Full documentation is available at: **https://devdenvino.github.io/fastapi_otel_common/**

- [Installation Guide](https://devdenvino.github.io/fastapi_otel_common/installation.html)
- [Configuration](https://devdenvino.github.io/fastapi_otel_common/configuration.html)
- [Middleware](https://devdenvino.github.io/fastapi_otel_common/middleware.html)
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
ENABLE_ERROR_HANDLING_MIDDLEWARE=True
ENABLE_RATE_LIMIT_MIDDLEWARE=True

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# OpenTelemetry
SERVICE_NAME=my-api
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## 🛡️ Security

Includes production-ready security features:

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

## 💾 Database

Async SQLAlchemy integration:

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

Full OpenTelemetry integration for distributed tracing:

- Automatic request tracing
- Database query tracing
- Custom span creation
- Context propagation
- Jaeger/OTLP export

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
