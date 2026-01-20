"""Database configuration and session management.

Provides async SQLAlchemy setup with connection pooling and Alembic integration.
Uses adapter pattern for flexible multi-database support.

Best Practices Implemented:
- Connection pool with pre-ping for stale connection handling
- Proper session lifecycle with rollback on exceptions
- Configurable pool settings for production workloads
- Health check utilities for monitoring
- Secure credential handling with URL encoding
"""
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from ..core.config import (
    DB_HOST,
    DB_MAX_OVERFLOW,
    DB_NAME,
    DB_PASS,
    DB_POOL_RECYCLE,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
    DB_PORT,
    DB_SCHEMA,
    DB_TYPE,
    DB_USER,
    ECHO_SQL,
    SQLITE_DB_PATH,
)
from ..logging.logger import get_logger
from .adapters import DatabaseAdapterFactory

logger = get_logger(__name__)

# Create database adapter based on DB_TYPE
# This makes it easy to add new database types - just create a new adapter class
if DB_TYPE == "sqlite":
    db_adapter = DatabaseAdapterFactory.create(
        "sqlite",
        db_path=SQLITE_DB_PATH,
    )
elif DB_TYPE == "mysql":
    db_adapter = DatabaseAdapterFactory.create(
        "mysql",
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
    )
else:  # postgresql (default)
    db_adapter = DatabaseAdapterFactory.create(
        "postgresql",
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        schema=DB_SCHEMA,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_recycle=DB_POOL_RECYCLE,
        pool_timeout=DB_POOL_TIMEOUT,
    )

# Get database URIs from adapter
SQLALCHEMY_DATABASE_URI_SYNC = db_adapter.get_sync_uri()
SQLALCHEMY_DATABASE_URI = db_adapter.get_async_uri()

# Create engine using adapter
engine = db_adapter.create_engine(echo=ECHO_SQL)
db_adapter.log_connection_info()

AsyncSessionLocal = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession)


# Base class for creating database models
# Use adapter to determine if schemas are supported
if "alembic" not in sys.argv[0]:
    metadata_kwargs = db_adapter.get_metadata_kwargs()
    Base = declarative_base(
        metadata=MetaData(**metadata_kwargs) if metadata_kwargs else None,
        cls=AsyncAttrs
    )
else:
    Base = declarative_base(cls=AsyncAttrs)


class BaseModel(Base):  # type: ignore
    """Base model class for all database models.
    
    Provides convenient methods for JSON serialization and deserialization.
    All model classes should inherit from this base.
    
    Example:
        class User(BaseModel):
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            name = Column(String)
    """
    __abstract__ = True

    def to_json(self) -> dict:
        """Convert model instance to JSON-serializable dictionary.
        
        Returns:
            dict: Dictionary with column names as keys and values.
                  Note: Does not serialize relationships by default.
        """
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def from_json(cls, json_data: dict) -> "BaseModel":
        """Create model instance from JSON dictionary.
        
        Args:
            json_data: Dictionary with model field values.
                       Keys should match column names.
            
        Returns:
            Instance of the model class
            
        Raises:
            TypeError: If json_data contains unknown fields
        """
        return cls(**json_data)
    
    def __repr__(self) -> str:
        """Return a string representation of the model instance."""
        class_name = self.__class__.__name__
        attrs = ", ".join(
            f"{c.name}={getattr(self, c.name)!r}"
            for c in self.__table__.columns
            if not c.name.startswith("_")
        )
        return f"{class_name}({attrs})"


async def init_models() -> None:
    """Initialize database models.
    
    If INIT_DB environment variable is 'true', it drops and creates all tables.
    
    Warning:
        This is a DESTRUCTIVE operation that will drop all existing tables
        and data. Should only be used in development/testing environments.
        
    Environment Variables:
        INIT_DB: Set to 'true' to enable table recreation
        
    Raises:
        SQLAlchemyError: If database operations fail
    """
    if os.getenv("INIT_DB", "").lower() == "true":
        logger.warning("INIT_DB=true: Dropping and recreating all tables!")
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized successfully.")
        except SQLAlchemyError as e:
            logger.error(f"Failed to initialize database tables: {e}")
            raise
    else:
        logger.debug("INIT_DB not set, using existing database schema.")


# Dependency to get DB session
@asynccontextmanager
async def get_db_session_with_async_context() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with async context manager.
    
    Provides automatic transaction management with rollback on exceptions.
    Sets the search_path to the configured schema for PostgreSQL.
    
    Example:
        async with get_db_session_with_async_context() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
    
    Yields:
        AsyncSession: Database session with transaction management
        
    Raises:
        SQLAlchemyError: If database operations fail
    """
    logger.debug("Acquiring database session...")
    async with AsyncSessionLocal() as session:
        try:
            # Execute database-specific session setup SQL (if any)
            # Split by semicolon to handle databases like SQLite that only allow one statement at a time
            setup_sql = db_adapter.get_session_setup_sql()
            if setup_sql:
                for stmt in setup_sql.split(';'):
                    stmt = stmt.strip()
                    if stmt:
                        await session.execute(text(stmt))
                await session.commit()
                logger.debug(f"Session setup executed: {setup_sql}")
            yield session
            # Commit if no exception occurred
            await session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Database error, rolling back transaction: {e}")
            await session.rollback()
            raise
        except Exception as e:
            logger.error(f"Unexpected error, rolling back transaction: {e}")
            await session.rollback()
            raise
        finally:
            logger.debug("Database session closed.")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get an async database session.
    
    Provides automatic transaction management with rollback on exceptions.
    Sets the search_path to the configured schema for PostgreSQL.
    
    Use this as a FastAPI dependency:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    
    Note:
        The session is automatically committed on success and rolled back
        on exceptions. You don't need to call commit() explicitly unless
        you want to commit mid-transaction.
    
    Yields:
        AsyncSession: Database session with transaction management
    """
    logger.debug("Acquiring database session for request...")

    async with AsyncSessionLocal() as session:
        try:
            # Execute database-specific session setup SQL (if any)
            # Split by semicolon to handle databases like SQLite that only allow one statement at a time
            setup_sql = db_adapter.get_session_setup_sql()
            if setup_sql:
                for stmt in setup_sql.split(';'):
                    stmt = stmt.strip()
                    if stmt:
                        await session.execute(text(stmt))
                await session.commit()
            yield session
            # Commit transaction if no exception occurred
            await session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Database error in request, rolling back: {e}")
            await session.rollback()
            raise
        except Exception as e:
            logger.warning(f"Exception during request, rolling back transaction: {e}")
            await session.rollback()
            raise
        finally:
            logger.debug("Request database session closed.")


async def close_db_connection() -> None:
    """Close the database connection engine and release all connections.
    
    Should be called during application shutdown to cleanly release
    all database connections from the pool.
    
    Example:
        @app.on_event("shutdown")
        async def shutdown():
            await close_db_connection()
    """
    logger.info("Closing database connection pool...")
    await engine.dispose()
    logger.info("Database connection pool closed.")


async def check_db_health() -> dict:
    """Check database connectivity and return health status.
    
    Performs a simple query to verify the database is accessible.
    Useful for health check endpoints and monitoring.
    
    Returns:
        dict: Health status with keys:
            - healthy (bool): Whether database is accessible
            - database_type (str): Type of database (postgresql, sqlite, etc.)
            - message (str): Status message or error description
            - latency_ms (float): Query latency in milliseconds (if healthy)
    
    Example:
        @app.get("/health/db")
        async def db_health():
            return await check_db_health()
    """
    import time
    
    start_time = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            # Use a simple query that works across all databases
            await session.execute(text("SELECT 1"))
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "healthy": True,
                "database_type": db_adapter.__class__.__name__.replace("Adapter", "").lower(),
                "message": "Database connection successful",
                "latency_ms": round(latency_ms, 2),
            }
    except SQLAlchemyError as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"Database health check failed: {e}")
        return {
            "healthy": False,
            "database_type": db_adapter.__class__.__name__.replace("Adapter", "").lower(),
            "message": f"Database connection failed: {str(e)}",
            "latency_ms": round(latency_ms, 2),
        }


def apply_migrations(alembic_config_path: str = "alembic.ini", revision: str = "head") -> None:
    """Apply alembic migrations to the database.
    
    Args:
        alembic_config_path: Path to the alembic.ini configuration file.
                            Defaults to "alembic.ini" in current directory.
        revision: Target revision to migrate to. Defaults to "head" (latest).
    
    Raises:
        FileNotFoundError: If alembic.ini is not found
        SQLAlchemyError: If database operations fail
        Exception: If migrations fail to apply
        
    Example:
        # Apply all pending migrations
        apply_migrations()
        
        # Apply to a specific revision
        apply_migrations(revision="abc123")
    """
    logger.info(f"Applying database migrations to revision '{revision}'...")
    
    if not os.path.exists(alembic_config_path):
        raise FileNotFoundError(
            f"Alembic configuration file not found: {alembic_config_path}"
        )
    
    try:
        alembic_cfg = Config(alembic_config_path)
        command.upgrade(alembic_cfg, revision)
        logger.info(f"Database migrations applied successfully to '{revision}'.")
    except SQLAlchemyError as e:
        logger.error(f"Database error during migration: {e}")
        raise
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
