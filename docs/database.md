---
layout: default
title: Database
nav_order: 6
---

# Database Guide
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

The database module provides async SQLAlchemy integration with connection pooling, session management, and Alembic migration support. It supports multiple database backends including PostgreSQL (production), MySQL, and SQLite (development).

**Key Features:**
- Automatic transaction management with commit/rollback
- Connection pool with pre-ping for stale connection recovery
- Health check utilities for monitoring
- URL-encoded credentials for special characters
- Configurable pool settings for production workloads

## Database Types

### PostgreSQL (Production)
Default database for production deployments with full feature support including schemas, connection pooling, and advanced PostgreSQL features.

### SQLite (Development)
Lightweight file-based database perfect for local development. No external database server required - just set `DB_TYPE=sqlite` and start coding!

## Configuration

### PostgreSQL Configuration

Configure your PostgreSQL connection using environment variables:

```bash
# Set database type
DB_TYPE=postgresql

# Connection settings
DB_USER=postgres
DB_PASS=postgres  # Supports special characters - automatically URL-encoded
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb
DB_SCHEMA=public

# Connection pool (production-ready defaults)
DB_POOL_SIZE=5         # Connections to maintain in pool
DB_MAX_OVERFLOW=10     # Max additional connections beyond pool_size
DB_POOL_RECYCLE=1800   # Recycle connections after 30 minutes
DB_POOL_TIMEOUT=30     # Timeout for getting connection from pool
# pool_pre_ping is enabled by default to detect stale connections

# Debug
ECHO_SQL=False
```

### SQLite Configuration

For quick development without setting up PostgreSQL:

```bash
# Set database type to SQLite
DB_TYPE=sqlite

# Path to SQLite database file (relative to project root or absolute)
SQLITE_DB_PATH=./data/app.db

# Optional: Initialize database with tables (DESTRUCTIVE - drops existing tables!)
INIT_DB=true

# Debug
ECHO_SQL=False
```

**SQLite Best Practices (enabled by default):**
- Foreign key constraints are enforced via `PRAGMA foreign_keys = ON`
- WAL mode is enabled for file-based databases for better concurrency
- Use `:memory:` for in-memory testing databases

**Note**: SQLite doesn't support database schemas, so `DB_SCHEMA` is ignored when using SQLite.

## Architecture: Multi-Database Support

This library uses the **Adapter Pattern** for database support, making it incredibly easy to add new database types without modifying existing code.

### Supported Databases

Out of the box, the following databases are supported:

- **PostgreSQL** (Production recommended) - Full feature support with schemas, pooling
- **SQLite** (Development) - File-based, zero configuration
- **MySQL/MariaDB** (Example included) - Ready to use with minimal setup

### Adding Custom Database Support

To add support for a new database (Oracle, MS SQL Server, CockroachDB, etc.):

1. **Create an Adapter Class**:

```python
from fastapi_otel_common.database import DatabaseAdapter, DatabaseAdapterFactory
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from urllib.parse import quote_plus
from typing import Any, Dict, Optional

class OracleAdapter(DatabaseAdapter):
    def __init__(
        self,
        user: str,
        password: str,
        host: str,
        port: str,
        service_name: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_recycle: int = 1800,
        pool_pre_ping: bool = True,
    ):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.service_name = service_name
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
    
    def _encode_credentials(self) -> tuple[str, str]:
        """URL-encode credentials for safe URI inclusion."""
        return quote_plus(self.user), quote_plus(self.password)
    
    def get_sync_uri(self) -> str:
        user, password = self._encode_credentials()
        return f"oracle+cx_oracle://{user}:{password}@{self.host}:{self.port}/?service_name={self.service_name}"
    
    def get_async_uri(self) -> str:
        user, password = self._encode_credentials()
        return f"oracle+oracledb_async://{user}:{password}@{self.host}:{self.port}/?service_name={self.service_name}"
    
    def create_engine(self, echo: bool = False) -> AsyncEngine:
        return create_async_engine(
            self.get_async_uri(),
            echo=echo,
            future=True,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_recycle=self.pool_recycle,
            pool_pre_ping=self.pool_pre_ping,
        )
    
    def get_metadata_kwargs(self) -> Dict[str, Any]:
        return {}
    
    def supports_schemas(self) -> bool:
        return True
    
    def get_session_setup_sql(self) -> Optional[str]:
        return None
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Return pool configuration for monitoring."""
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
        }
    
    def log_connection_info(self) -> None:
        # Log connection info (without password!)
        pass
```

2. **Register the Adapter**:

```python
DatabaseAdapterFactory.register_adapter("oracle", OracleAdapter)

# Check available adapters
print(DatabaseAdapterFactory.get_supported_types())
# ['postgresql', 'sqlite', 'mysql', 'oracle']
```

3. **Use It**:

```bash
DB_TYPE=oracle
```

That's it! See [examples/example_custom_database.py](../examples/example_custom_database.py) for complete examples.

### Benefits of the Adapter Pattern

- **Open/Closed Principle**: Add new databases without modifying existing code
- **Single Responsibility**: Each adapter handles one database type
- **Easy Testing**: Mock adapters for testing
- **Maintainability**: Database-specific logic is isolated
- **Extensibility**: Anyone can add support for their database

## Database Session

### Automatic Transaction Management

Sessions automatically handle transactions:
- **On success**: Transaction is committed
- **On exception**: Transaction is rolled back
- **Always**: Session is properly closed

You don't need to call `commit()` or `rollback()` manually unless you want mid-transaction commits.

### Using as FastAPI Dependency

```python
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_otel_common.database import get_db_session

app = FastAPI()

@app.get("/users")
async def get_users(db: AsyncSession = Depends(get_db_session)):
    from sqlalchemy import select
    from .models import User
    
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users  # Transaction auto-committed on success
```

### Using with Context Manager

```python
from fastapi_otel_common.database import get_db_session_with_async_context

async def process_data():
    async with get_db_session_with_async_context() as db:
        # Your database operations
        result = await db.execute(select(User))
        users = result.scalars().all()
        return users  # Transaction auto-committed when exiting context

async def create_users():
    async with get_db_session_with_async_context() as db:
        try:
            db.add(User(email="user1@example.com"))
            db.add(User(email="user2@example.com"))
            # If an exception occurs here, transaction is rolled back
        except Exception:
            # Rollback happens automatically
            raise
        # Commit happens automatically on successful exit
```

## Database Health Check

The library provides a built-in health check utility for monitoring database connectivity:

```python
from fastapi import FastAPI
from fastapi_otel_common.database import check_db_health

app = FastAPI()

@app.get("/health/db")
async def db_health():
    return await check_db_health()
```

**Response (healthy):**
```json
{
  "healthy": true,
  "database_type": "postgresql",
  "message": "Database connection successful",
  "latency_ms": 2.45
}
```

**Response (unhealthy):**
```json
{
  "healthy": false,
  "database_type": "postgresql",
  "message": "Database connection failed: connection refused",
  "latency_ms": 5002.31
}
```

## Defining Models

### Using BaseModel

```python
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, UTC
from fastapi_otel_common.database import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

# BaseModel provides automatic __repr__ for debugging
user = User(email="user@example.com", username="john")
print(user)  # User(id=1, email='user@example.com', username='john', ...)
```
    username = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<User(email='{self.email}')>"
```

### JSON Serialization

The `BaseModel` provides convenient JSON methods:

```python
# Convert to JSON
user = User(email="user@example.com", username="john")
user_dict = user.to_json()
# {"id": 1, "email": "user@example.com", "username": "john", ...}

# Create from JSON
user_data = {"email": "user@example.com", "username": "john"}
user = User.from_json(user_data)
```

## Database Operations

### Create

```python
@app.post("/users")
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session)
):
    user = User(
        email=user_data.email,
        username=user_data.username
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
```

### Read

```python
from sqlalchemy import select

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user
```

### Update

```python
@app.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.email = user_data.email
    user.username = user_data.username
    
    await db.commit()
    await db.refresh(user)
    return user
```

### Delete

```python
@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted"}
```

## Alembic Migrations

### Setup

1. Create `alembic.ini` in your project root:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

[alembic:exclude]
tables = spatial_ref_sys

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

2. Initialize Alembic:

```bash
alembic init alembic
```

3. Create `alembic/env.py`:

```python
from fastapi_otel_common.database import Base
from fastapi_otel_common.database.alembic import run_migrations_offline, run_migrations_online
from alembic import context

# Import your models here
from myapp.models import User, Post, Comment

# Set target metadata
target_metadata = Base.metadata

if context.is_offline_mode():
    run_migrations_offline(target_metadata)
else:
    run_migrations_online(target_metadata)
    # NOTE: Do NOT wrap in asyncio.run() - these are synchronous functions
```

### Create Migration

```bash
alembic revision --autogenerate -m "Create users table"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback

```bash
alembic downgrade -1  # Rollback one version
alembic downgrade base  # Rollback all
```

## Connection Pooling

The library uses SQLAlchemy's async connection pooling with production-ready defaults:

```python
# Configured via environment variables
DB_POOL_SIZE=5          # Number of connections to maintain
DB_MAX_OVERFLOW=10      # Max connections beyond pool_size
DB_POOL_RECYCLE=1800    # Recycle connections after 30 minutes (was 3600)
DB_POOL_TIMEOUT=30      # Timeout for getting connection
```

**Best Practices (enabled by default):**
- **pool_pre_ping**: Automatically tests connections before use, recovering from stale connections
- **pool_recycle**: Set to 1800 seconds (30 min) to prevent connections from going stale
- **URL encoding**: Passwords with special characters are automatically encoded

## Multi-Schema Support

The library supports PostgreSQL schemas:

```bash
DB_SCHEMA=myschema
```

All tables will be created in the specified schema. Migrations automatically handle schema creation.

## Best Practices

1. **Use connection pooling** - Configured by default with pre-ping for stale connection recovery
2. **Always use async operations** - Use `await` for all database calls
3. **Let sessions auto-manage transactions** - Don't manually commit/rollback unless necessary
4. **Handle exceptions** - SQLAlchemy errors are caught and logged, transactions auto-rollback
5. **Use migrations** - Track schema changes with Alembic
6. **Index frequently queried fields** - Add indexes to improve performance
7. **Use the health check endpoint** - Monitor database connectivity via `check_db_health()`
8. **Use special character passwords safely** - Credentials are automatically URL-encoded

## Example: Complete CRUD Application

```python
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel as PydanticBase

from fastapi_otel_common import create_app
from fastapi_otel_common.database import BaseModel, get_db_session, check_db_health

# Create app with automatic OpenTelemetry instrumentation
app = create_app(title="User API", version="1.0.0")

# Database model
class User(BaseModel):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)

# Pydantic models
class UserCreate(PydanticBase):
    email: str
    username: str

class UserResponse(PydanticBase):
    id: int
    email: str
    username: str
    
    class Config:
        from_attributes = True

# Health check endpoint
@app.get("/health/db")
async def db_health():
    return await check_db_health()

# Routes - Note: No manual commit() needed, auto-managed!
@app.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session)
):
    user = User(**user_data.model_dump())
    db.add(user)
    await db.flush()  # Flush to get the ID
    await db.refresh(user)
    return user  # Auto-commit on success

@app.get("/users", response_model=list[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(User))
    return result.scalars().all()

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

## Troubleshooting

### Connection Pool Exhausted

Increase pool size:
```bash
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

### Slow Queries

Enable SQL logging:
```bash
ECHO_SQL=True
```

### Schema Not Found

Ensure schema exists and user has permissions:
```sql
CREATE SCHEMA IF NOT EXISTS myschema;
GRANT ALL ON SCHEMA myschema TO myuser;
```

## Next Steps

- [Examples](examples) - See complete examples
- [API Reference](api) - Full API documentation
