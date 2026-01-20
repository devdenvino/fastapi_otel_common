"""Database adapter classes for different database backends.

Implements the Adapter pattern to support multiple database types with
consistent interface. Makes it easy to add new database backends.

Best Practices Implemented:
- Pool pre-ping for automatic stale connection recovery
- URL encoding for credentials with special characters
- Configurable pool settings for production workloads
- Connection pool recycling to prevent stale connections
"""
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from ..logging.logger import get_logger

logger = get_logger(__name__)


class DatabaseAdapter(ABC):
    """Abstract base class for database adapters.
    
    Each database type (PostgreSQL, SQLite, MySQL, etc.) should implement
    this interface to provide database-specific configuration.
    
    When implementing a custom adapter:
    1. Inherit from this class
    2. Implement all abstract methods
    3. Register with DatabaseAdapterFactory.register_adapter()
    """
    
    @abstractmethod
    def get_sync_uri(self) -> str:
        """Get synchronous database URI for migrations.
        
        Returns:
            str: Database URI compatible with synchronous drivers
        """
        pass
    
    @abstractmethod
    def get_async_uri(self) -> str:
        """Get asynchronous database URI for application use.
        
        Returns:
            str: Database URI compatible with async drivers (asyncpg, aiosqlite, etc.)
        """
        pass
    
    @abstractmethod
    def create_engine(self, echo: bool = False) -> AsyncEngine:
        """Create and configure SQLAlchemy async engine.
        
        Args:
            echo: If True, log all SQL statements
            
        Returns:
            AsyncEngine: Configured SQLAlchemy async engine
        """
        pass
    
    @abstractmethod
    def get_metadata_kwargs(self) -> Dict[str, Any]:
        """Get kwargs for MetaData initialization (e.g., schema).
        
        Returns:
            Dict containing metadata configuration options
        """
        pass
    
    @abstractmethod
    def supports_schemas(self) -> bool:
        """Whether this database supports schemas.
        
        Returns:
            bool: True if database supports schema separation
        """
        pass
    
    @abstractmethod
    def get_session_setup_sql(self) -> Optional[str]:
        """Get SQL to run when creating a session (e.g., SET search_path).
        
        Returns:
            Optional[str]: SQL statement to execute, or None if not needed
        """
        pass
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get connection pool status information.
        
        Returns:
            Dict with pool configuration (override for pool statistics)
        """
        return {"pool_info": "Not available for this adapter"}
    
    def log_connection_info(self) -> None:
        """Log database connection information (without sensitive data)."""
        logger.info(f"Database adapter initialized: {self.__class__.__name__}")


class PostgreSQLAdapter(DatabaseAdapter):
    """Adapter for PostgreSQL databases.
    
    Supports:
    - Async connections via asyncpg driver
    - Schema separation with search_path
    - Connection pooling with pre-ping
    - Automatic connection recycling
    
    Args:
        user: Database username
        password: Database password (will be URL-encoded)
        host: Database host
        port: Database port
        database: Database name
        schema: PostgreSQL schema name
        pool_size: Number of connections to keep in pool (default: 5)
        max_overflow: Max connections beyond pool_size (default: 10)
        pool_recycle: Seconds before connection is recycled (default: 1800)
        pool_timeout: Seconds to wait for connection (default: 30)
        pool_pre_ping: Test connections before use (default: True)
    """
    
    def __init__(
        self,
        user: str,
        password: str,
        host: str,
        port: str,
        database: str,
        schema: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_recycle: int = 1800,
        pool_timeout: int = 30,
        pool_pre_ping: bool = True,
    ):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.database = database
        self.schema = schema
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_recycle = pool_recycle
        self.pool_timeout = pool_timeout
        self.pool_pre_ping = pool_pre_ping
    
    def _encode_credentials(self) -> tuple[str, str]:
        """URL-encode user and password for safe URI inclusion."""
        return quote_plus(self.user), quote_plus(self.password)
    
    def get_sync_uri(self) -> str:
        user, password = self._encode_credentials()
        return f"postgresql://{user}:{password}@{self.host}:{self.port}/{self.database}"
    
    def get_async_uri(self) -> str:
        user, password = self._encode_credentials()
        return f"postgresql+asyncpg://{user}:{password}@{self.host}:{self.port}/{self.database}"
    
    def create_engine(self, echo: bool = False) -> AsyncEngine:
        return create_async_engine(
            self.get_async_uri(),
            echo=echo,
            future=True,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_recycle=self.pool_recycle,
            pool_timeout=self.pool_timeout,
            pool_pre_ping=self.pool_pre_ping,
        )
    
    def get_metadata_kwargs(self) -> Dict[str, Any]:
        return {"schema": self.schema}
    
    def supports_schemas(self) -> bool:
        return True
    
    def get_session_setup_sql(self) -> Optional[str]:
        return f"SET search_path TO {self.schema};"
    
    def get_pool_status(self) -> Dict[str, Any]:
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_recycle": self.pool_recycle,
            "pool_timeout": self.pool_timeout,
            "pool_pre_ping": self.pool_pre_ping,
        }
    
    def log_connection_info(self) -> None:
        logger.info(
            f"PostgreSQL connection: {self.database}@{self.host}:{self.port} "
            f"(schema={self.schema}, pool_size={self.pool_size}, "
            f"max_overflow={self.max_overflow}, pre_ping={self.pool_pre_ping})"
        )


class SQLiteAdapter(DatabaseAdapter):
    """Adapter for SQLite databases.
    
    Supports:
    - In-memory databases with :memory:
    - File-based databases with automatic directory creation
    - WAL mode for better concurrent access
    - Foreign key enforcement
    
    Args:
        db_path: Path to SQLite database file, or ":memory:" for in-memory
        enable_foreign_keys: Enable foreign key constraints (default: True)
        enable_wal_mode: Enable WAL mode for better concurrency (default: True)
    """
    
    def __init__(
        self,
        db_path: str,
        enable_foreign_keys: bool = True,
        enable_wal_mode: bool = True,
    ):
        self.db_path = db_path
        self.enable_foreign_keys = enable_foreign_keys
        self.enable_wal_mode = enable_wal_mode
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self) -> None:
        """Create directory for SQLite database if it doesn't exist."""
        if self.db_path != ":memory:":
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                logger.debug(f"Created directory for SQLite database: {db_dir}")
    
    def get_sync_uri(self) -> str:
        return f"sqlite:///{self.db_path}"
    
    def get_async_uri(self) -> str:
        return f"sqlite+aiosqlite:///{self.db_path}"
    
    def create_engine(self, echo: bool = False) -> AsyncEngine:
        return create_async_engine(
            self.get_async_uri(),
            echo=echo,
            future=True,
            connect_args={"check_same_thread": False},
        )
    
    def get_metadata_kwargs(self) -> Dict[str, Any]:
        return {}  # SQLite doesn't support schemas
    
    def supports_schemas(self) -> bool:
        return False
    
    def get_session_setup_sql(self) -> Optional[str]:
        """Return SQL to configure SQLite session (foreign keys, WAL mode)."""
        statements = []
        if self.enable_foreign_keys:
            statements.append("PRAGMA foreign_keys = ON")
        if self.enable_wal_mode and self.db_path != ":memory:":
            statements.append("PRAGMA journal_mode = WAL")
        return "; ".join(statements) + ";" if statements else None
    
    def log_connection_info(self) -> None:
        mode = "in-memory" if self.db_path == ":memory:" else f"file: {self.db_path}"
        logger.info(
            f"SQLite connection: {mode} "
            f"(foreign_keys={self.enable_foreign_keys}, wal_mode={self.enable_wal_mode})"
        )


class MySQLAdapter(DatabaseAdapter):
    """Adapter for MySQL/MariaDB databases.
    
    Supports:
    - Async connections via aiomysql driver
    - Connection pooling with pre-ping
    - UTF-8 charset configuration
    - Automatic connection recycling
    
    Args:
        user: Database username
        password: Database password (will be URL-encoded)
        host: Database host
        port: Database port
        database: Database name
        pool_size: Number of connections to keep in pool (default: 5)
        max_overflow: Max connections beyond pool_size (default: 10)
        pool_recycle: Seconds before connection is recycled (default: 1800)
        pool_pre_ping: Test connections before use (default: True)
        charset: Character set to use (default: utf8mb4)
    """
    
    def __init__(
        self,
        user: str,
        password: str,
        host: str,
        port: str,
        database: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_recycle: int = 1800,
        pool_pre_ping: bool = True,
        charset: str = "utf8mb4",
    ):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.database = database
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.charset = charset
    
    def _encode_credentials(self) -> tuple[str, str]:
        """URL-encode user and password for safe URI inclusion."""
        return quote_plus(self.user), quote_plus(self.password)
    
    def get_sync_uri(self) -> str:
        user, password = self._encode_credentials()
        return f"mysql://{user}:{password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"
    
    def get_async_uri(self) -> str:
        user, password = self._encode_credentials()
        return f"mysql+aiomysql://{user}:{password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"
    
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
        return {}  # MySQL has databases instead of schemas
    
    def supports_schemas(self) -> bool:
        return False
    
    def get_session_setup_sql(self) -> Optional[str]:
        """Set MySQL session configuration (charset, timezone, SQL mode)."""
        return f"SET NAMES {self.charset}; SET sql_mode='TRADITIONAL';"
    
    def get_pool_status(self) -> Dict[str, Any]:
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
        }
    
    def log_connection_info(self) -> None:
        logger.info(
            f"MySQL connection: {self.database}@{self.host}:{self.port} "
            f"(charset={self.charset}, pool_size={self.pool_size}, "
            f"max_overflow={self.max_overflow}, pre_ping={self.pool_pre_ping})"
        )


class DatabaseAdapterFactory:
    """Factory for creating database adapters based on configuration.
    
    Uses the Factory pattern to decouple adapter creation from usage.
    Allows easy extension with custom database adapters.
    
    To add a new database type:
        1. Create a new adapter class inheriting from DatabaseAdapter
        2. Register it: DatabaseAdapterFactory.register_adapter("mydb", MyDBAdapter)
        3. Use it: adapter = DatabaseAdapterFactory.create("mydb", **config)
    
    Example:
        # Register custom adapter
        class CockroachDBAdapter(DatabaseAdapter):
            # ... implementation ...
        
        DatabaseAdapterFactory.register_adapter("cockroachdb", CockroachDBAdapter)
        
        # Create adapter instance
        adapter = DatabaseAdapterFactory.create(
            "postgresql",
            user="myuser",
            password="mypass",
            host="localhost",
            port="5432",
            database="mydb",
            schema="public",
        )
    """
    
    _adapters: Dict[str, type[DatabaseAdapter]] = {}
    
    @classmethod
    def register_adapter(cls, db_type: str, adapter_class: type[DatabaseAdapter]) -> None:
        """Register a database adapter for a specific type.
        
        Args:
            db_type: Unique identifier for the database type (case-insensitive)
            adapter_class: Class that implements DatabaseAdapter interface
        """
        cls._adapters[db_type.lower()] = adapter_class
        logger.debug(f"Registered database adapter: {db_type} -> {adapter_class.__name__}")
    
    @classmethod
    def unregister_adapter(cls, db_type: str) -> bool:
        """Unregister a database adapter.
        
        Args:
            db_type: Database type to unregister
            
        Returns:
            bool: True if adapter was removed, False if it didn't exist
        """
        db_type = db_type.lower()
        if db_type in cls._adapters:
            del cls._adapters[db_type]
            logger.debug(f"Unregistered database adapter: {db_type}")
            return True
        return False
    
    @classmethod
    def get_supported_types(cls) -> list[str]:
        """Get list of all registered database types.
        
        Returns:
            List of supported database type identifiers
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def create(cls, db_type: str, **kwargs: Any) -> DatabaseAdapter:
        """Create appropriate database adapter based on type.
        
        Args:
            db_type: Database type ('postgresql', 'sqlite', 'mysql', etc.)
            **kwargs: Configuration parameters for the adapter
            
        Returns:
            DatabaseAdapter instance configured with provided parameters
            
        Raises:
            ValueError: If database type is not supported
            TypeError: If required parameters are missing
        """
        db_type_lower = db_type.lower()
        adapter_class = cls._adapters.get(db_type_lower)
        
        if not adapter_class:
            supported = ", ".join(sorted(cls._adapters.keys()))
            raise ValueError(
                f"Unsupported database type: '{db_type}'. "
                f"Supported types: {supported}. "
                f"Use DatabaseAdapterFactory.register_adapter() to add custom adapters."
            )
        
        try:
            return adapter_class(**kwargs)
        except TypeError as e:
            raise TypeError(
                f"Invalid parameters for {adapter_class.__name__}: {e}"
            ) from e


# Register built-in adapters
DatabaseAdapterFactory.register_adapter("postgresql", PostgreSQLAdapter)
DatabaseAdapterFactory.register_adapter("sqlite", SQLiteAdapter)
DatabaseAdapterFactory.register_adapter("mysql", MySQLAdapter)
