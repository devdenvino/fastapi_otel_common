"""Example: Adding Custom Database Support

This example demonstrates how easy it is to add support for a new database type
using the adapter pattern. You can add support for any SQLAlchemy-compatible
database (Oracle, MS SQL Server, CockroachDB, etc.) by creating a simple adapter.

Best Practices Demonstrated:
- URL encoding for credentials with special characters
- Connection pool with pre-ping for stale connection recovery
- Configurable pool settings for production workloads
"""
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from fastapi_otel_common.database import (
    DatabaseAdapter,
    DatabaseAdapterFactory,
)


# Example 1: Add Oracle Database Support
class OracleAdapter(DatabaseAdapter):
    """Adapter for Oracle databases.
    
    Supports:
    - Async connections via oracledb driver
    - Connection pooling with pre-ping
    - URL-encoded credentials for special characters
    """
    
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
        """URL-encode user and password for safe URI inclusion."""
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
        return {}  # Oracle uses schemas differently
    
    def supports_schemas(self) -> bool:
        return True
    
    def get_session_setup_sql(self) -> Optional[str]:
        return None  # Or return "ALTER SESSION SET ..." if needed
    
    def get_pool_status(self) -> Dict[str, Any]:
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
        }
    
    def log_connection_info(self) -> None:
        from fastapi_otel_common.logging import get_logger
        logger = get_logger(__name__)
        logger.info(
            f"Oracle connection: {self.service_name}@{self.host}:{self.port} "
            f"(pool_size={self.pool_size}, pre_ping={self.pool_pre_ping})"
        )


# Example 2: Add Microsoft SQL Server Support
class MSSQLAdapter(DatabaseAdapter):
    """Adapter for Microsoft SQL Server.
    
    Supports:
    - Async connections via aioodbc driver
    - Connection pooling with pre-ping
    - Configurable ODBC driver
    """
    
    def __init__(
        self,
        user: str,
        password: str,
        host: str,
        port: str,
        database: str,
        driver: str = "ODBC Driver 17 for SQL Server",
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_recycle: int = 1800,
        pool_pre_ping: bool = True,
    ):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.database = database
        self.driver = driver
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
    
    def _encode_credentials(self) -> tuple[str, str]:
        """URL-encode user and password for safe URI inclusion."""
        return quote_plus(self.user), quote_plus(self.password)
    
    def get_sync_uri(self) -> str:
        user, password = self._encode_credentials()
        driver_encoded = quote_plus(self.driver)
        return f"mssql+pyodbc://{user}:{password}@{self.host}:{self.port}/{self.database}?driver={driver_encoded}"
    
    def get_async_uri(self) -> str:
        user, password = self._encode_credentials()
        driver_encoded = quote_plus(self.driver)
        return f"mssql+aioodbc://{user}:{password}@{self.host}:{self.port}/{self.database}?driver={driver_encoded}"
    
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
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
        }
    
    def log_connection_info(self) -> None:
        from fastapi_otel_common.logging import get_logger
        logger = get_logger(__name__)
        logger.info(
            f"MS SQL Server connection: {self.database}@{self.host}:{self.port} "
            f"(pool_size={self.pool_size}, pre_ping={self.pool_pre_ping})"
        )


# Register the new adapters
DatabaseAdapterFactory.register_adapter("oracle", OracleAdapter)
DatabaseAdapterFactory.register_adapter("mssql", MSSQLAdapter)

# Now you can use them by setting DB_TYPE environment variable:
# DB_TYPE=oracle
# DB_TYPE=mssql

# You can also check what adapters are available:
print("✓ Custom database adapters registered successfully!")
print(f"\nSupported database types: {DatabaseAdapterFactory.get_supported_types()}")

print("\nTo use Oracle:")
print("  Set: DB_TYPE=oracle")
print("  Install: pip install oracledb cx_Oracle")
print("\nTo use MS SQL Server:")
print("  Set: DB_TYPE=mssql")
print("  Install: pip install pyodbc aioodbc")
print("\nBest practices enabled by default:")
print("  - pool_pre_ping: Auto-recover from stale connections")
print("  - pool_recycle: Connections recycled every 30 minutes")
print("  - URL encoding: Passwords with special characters supported")
print("\nThe adapter pattern makes it easy to support any database!")
