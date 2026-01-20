---
layout: default
title: Examples
nav_order: 7
---

# Examples
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Basic FastAPI Application

```python
from fastapi_otel_common import create_app

# Create app with all middleware enabled and automatic OpenTelemetry instrumentation
app = create_app(
    title="My API",
    version="1.0.0",
    description="Production-ready API with OpenTelemetry"
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

## Secured Application with Authentication

```python
from fastapi import Depends, HTTPException
from fastapi_otel_common import create_app
from fastapi_otel_common.security import get_current_user, get_current_user_optional
from fastapi_otel_common.core.models import UserBase

app = create_app(title="Secure API", version="1.0.0")

@app.get("/public")
async def public_endpoint():
    return {"message": "This is public"}

@app.get("/profile")
async def get_profile(user: UserBase = Depends(get_current_user)):
    return {
        "user_id": user.id,
        "email": user.email,
        "name": f"{user.given_name} {user.family_name}"
    }

@app.get("/optional-auth")
async def optional_auth(user: UserBase | None = Depends(get_current_user_optional)):
    if user:
        return {"message": f"Hello, {user.given_name}!"}
    return {"message": "Hello, anonymous!"}

@app.post("/admin-only")
async def admin_only(user: UserBase = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"message": "Admin access granted"}
```

## Application with Database

```python
from fastapi import Depends, HTTPException
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from fastapi_otel_common import create_app
from fastapi_otel_common.database import BaseModel as DBBase, get_db_session
from fastapi_otel_common.security import get_current_user
from fastapi_otel_common.core.models import UserBase

# Database Model
class Item(DBBase):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    owner_id = Column(String)

# Pydantic Models
class ItemCreate(BaseModel):
    title: str
    description: str

class ItemResponse(BaseModel):
    id: int
    title: str
    description: str
    owner_id: str
    
    class Config:
        from_attributes = True

# Create app
app = create_app(title="Items API", version="1.0.0")

# Routes
@app.post("/items", response_model=ItemResponse)
async def create_item(
    item_data: ItemCreate,
    user: UserBase = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    item = Item(
        title=item_data.title,
        description=item_data.description,
        owner_id=user.id
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@app.get("/items", response_model=list[ItemResponse])
async def list_items(
    user: UserBase = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    result = await db.execute(
        select(Item).where(Item.owner_id == user.id)
    )
    return result.scalars().all()

@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    user: UserBase = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    result = await db.execute(
        select(Item).where(Item.id == item_id, Item.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return item

@app.delete("/items/{item_id}")
async def delete_item(
    item_id: int,
    user: UserBase = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    result = await db.execute(
        select(Item).where(Item.id == item_id, Item.owner_id == user.id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    await db.delete(item)
    await db.commit()
    return {"message": "Item deleted"}
```

## Custom Rate Limiting

```python
from fastapi import Request
from fastapi_otel_common import create_app

app = create_app(
    title="Rate Limited API",
    version="1.0.0"
)

# Access the limiter from app state
limiter = app.state.limiter

@app.get("/standard")
async def standard_endpoint():
    # Uses global rate limit (from env vars)
    return {"message": "Standard rate limit"}

@app.get("/expensive")
@limiter.limit("5/minute")
async def expensive_endpoint(request: Request):
    # Custom rate limit: 5 requests per minute
    return {"message": "Expensive operation"}

@app.get("/premium")
@limiter.limit("100/minute;1000/hour")
async def premium_endpoint(request: Request):
    # Multiple limits
    return {"message": "Premium endpoint"}
```

## Manual Middleware Configuration

```python
from fastapi import FastAPI
from fastapi_otel_common import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)

app = FastAPI(title="Custom Middleware", version="1.0.0")

# Add middleware manually in order (last added executes first)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=100,
    requests_per_hour=5000
)
app.add_middleware(RequestIDMiddleware)

# Note: OpenTelemetry instrumentation must be added manually when not using create_app()
# from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
# FastAPIInstrumentor.instrument_app(app)

@app.get("/")
async def root():
    return {"message": "Custom middleware setup"}
```

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - APP_TITLE=My API
      - DEBUG=False
      - DB_HOST=postgres
      - DB_USER=postgres
      - DB_PASS=postgres
      - DB_NAME=mydb
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
      - OIDC_DISCOVERY_URL=https://auth.example.com/.well-known/openid-configuration
      - ENABLE_RATE_LIMIT_MIDDLEWARE=True
    depends_on:
      - postgres
      - jaeger
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=mydb
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # Jaeger UI
      - "4317:4317"    # OTLP gRPC
    environment:
      - COLLECTOR_OTLP_ENABLED=true

volumes:
  postgres_data:
```

## Environment Configuration Example

### .env

```bash
# Application
APP_TITLE=My Production API
APP_VERSION=1.0.0
DEBUG=False
LOG_LEVEL=INFO

# OIDC
OIDC_DISCOVERY_URL=https://auth.example.com/.well-known/openid-configuration
OIDC_CLIENT_ID=my-client-id
OIDC_AUDIENCE=account
SWAGGER_CLIENT_ID=swagger-client-id

# CORS
ALLOWED_ORIGINS=https://myapp.example.com

# Database
DB_USER=postgres
DB_PASS=secure_password
DB_HOST=postgres
DB_PORT=5432
DB_NAME=production_db
DB_SCHEMA=public
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Middleware
ENABLE_REQUEST_ID_MIDDLEWARE=True
ENABLE_SECURITY_HEADERS_MIDDLEWARE=True
ENABLE_LOGGING_MIDDLEWARE=True
ENABLE_ERROR_HANDLING_MIDDLEWARE=True
ENABLE_RATE_LIMIT_MIDDLEWARE=True

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=5000

# OpenTelemetry
SERVICE_NAME=my-api
SERVICE_VERSION=1.0.0
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

## Next Steps

- [Configuration Guide](configuration) - Detailed configuration
- [Security Guide](security) - Authentication setup
- [Database Guide](database) - Database integration
- [Middleware Guide](middleware) - Middleware details
