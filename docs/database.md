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

The database module provides async SQLAlchemy integration with connection pooling, session management, and Alembic migration support.

## Configuration

Configure your database connection using environment variables:

```bash
# Connection settings
DB_USER=postgres
DB_PASS=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb
DB_SCHEMA=public

# Connection pool
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=3600
DB_POOL_TIMEOUT=30

# Debug
ECHO_SQL=False
```

## Database Session

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
    return users
```

### Using with Context Manager

```python
from fastapi_otel_common.database import get_db_session_with_async_context

async def process_data():
    async with get_db_session_with_async_context() as db:
        # Your database operations
        result = await db.execute(select(User))
        users = result.scalars().all()
        return users
```

## Defining Models

### Using BaseModel

```python
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from fastapi_otel_common.database import BaseModel

class User(BaseModel):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
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

The library uses SQLAlchemy's async connection pooling:

```python
# Configured via environment variables
DB_POOL_SIZE=5          # Number of connections to maintain
DB_MAX_OVERFLOW=10      # Max connections beyond pool_size
DB_POOL_RECYCLE=3600    # Recycle connections after 1 hour
DB_POOL_TIMEOUT=30      # Timeout for getting connection
```

## Multi-Schema Support

The library supports PostgreSQL schemas:

```bash
DB_SCHEMA=myschema
```

All tables will be created in the specified schema. Migrations automatically handle schema creation.

## Best Practices

1. **Use connection pooling** - Configured by default
2. **Always use async operations** - Use `await` for all database calls
3. **Use sessions properly** - Always close sessions (handled by dependency)
4. **Handle exceptions** - Catch database errors appropriately
5. **Use migrations** - Track schema changes with Alembic
6. **Index frequently queried fields** - Add indexes to improve performance
7. **Use transactions** - Wrap multiple operations in transactions

## Example: Complete CRUD Application

```python
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel as PydanticBase

from fastapi_otel_common import create_app, instrument_app
from fastapi_otel_common.database import BaseModel, get_db_session

# Create app
app = create_app(title="User API", version="1.0.0")
instrument_app(app)

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

# Routes
@app.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session)
):
    user = User(**user_data.dict())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

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

- [Examples](examples.md) - See complete examples
- [API Reference](api.md) - Full API documentation
