"""Database module exports.

Provides async database session management and base models.
Supports multiple database backends via adapter pattern.
"""
from .adapters import (
    DatabaseAdapter,
    DatabaseAdapterFactory,
    MySQLAdapter,
    PostgreSQLAdapter,
    SQLiteAdapter,
)
from .db import (
    AsyncSessionLocal,
    Base,
    BaseModel,
    apply_migrations,
    check_db_health,
    close_db_connection,
    db_adapter,
    engine,
    get_db_session,
    get_db_session_with_async_context,
    init_models,
)

__all__ = [
    # Database session and models
    "AsyncSessionLocal",
    "Base",
    "BaseModel",
    "apply_migrations",
    "check_db_health",
    "close_db_connection",
    "db_adapter",
    "engine",
    "get_db_session",
    "get_db_session_with_async_context",
    "init_models",
    # Adapter pattern for multi-database support
    "DatabaseAdapter",
    "DatabaseAdapterFactory",
    "PostgreSQLAdapter",
    "SQLiteAdapter",
    "MySQLAdapter",
]
