"""Test database adapters.

Verifies that the adapter pattern works correctly for different database types.
"""
import os
import pytest

# Set test environment before importing
os.environ["DB_TYPE"] = "sqlite"
os.environ["SQLITE_DB_PATH"] = ":memory:"
os.environ["OIDC_DISCOVERY_URL"] = "http://localhost/test"

from fastapi_otel_common.database.adapters import (
    DatabaseAdapter,
    DatabaseAdapterFactory,
    MySQLAdapter,
    PostgreSQLAdapter,
    SQLiteAdapter,
)


def test_sqlite_adapter():
    """Test SQLite adapter creation and configuration."""
    adapter = DatabaseAdapterFactory.create("sqlite", db_path=":memory:")
    
    assert isinstance(adapter, SQLiteAdapter)
    assert adapter.get_sync_uri() == "sqlite:///:memory:"
    assert adapter.get_async_uri() == "sqlite+aiosqlite:///:memory:"
    assert not adapter.supports_schemas()
    # In-memory SQLite gets foreign keys enabled but not WAL mode
    assert adapter.get_session_setup_sql() == "PRAGMA foreign_keys = ON;"
    assert adapter.get_metadata_kwargs() == {}


def test_postgresql_adapter():
    """Test PostgreSQL adapter creation and configuration."""
    adapter = DatabaseAdapterFactory.create(
        "postgresql",
        user="testuser",
        password="testpass",
        host="localhost",
        port="5432",
        database="testdb",
        schema="testschema",
        pool_size=5,
        max_overflow=10,
        pool_recycle=3600,
        pool_timeout=30,
    )
    
    assert isinstance(adapter, PostgreSQLAdapter)
    assert "postgresql://" in adapter.get_sync_uri()
    assert "postgresql+asyncpg://" in adapter.get_async_uri()
    assert adapter.supports_schemas()
    assert adapter.get_session_setup_sql() == "SET search_path TO testschema;"
    assert adapter.get_metadata_kwargs() == {"schema": "testschema"}


def test_mysql_adapter():
    """Test MySQL adapter creation and configuration."""
    adapter = DatabaseAdapterFactory.create(
        "mysql",
        user="testuser",
        password="testpass",
        host="localhost",
        port="3306",
        database="testdb",
        pool_size=5,
        max_overflow=10,
    )
    
    assert isinstance(adapter, MySQLAdapter)
    assert "mysql://" in adapter.get_sync_uri()
    assert "mysql+aiomysql://" in adapter.get_async_uri()
    assert not adapter.supports_schemas()
    # MySQL now sets charset and strict SQL mode for best practices
    assert adapter.get_session_setup_sql() == "SET NAMES utf8mb4; SET sql_mode='TRADITIONAL';"
    assert adapter.get_metadata_kwargs() == {}


def test_unsupported_database_type():
    """Test that unsupported database types raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported database type"):
        DatabaseAdapterFactory.create("unsupported_db")


def test_custom_adapter_registration():
    """Test that custom adapters can be registered."""
    
    class CustomAdapter(DatabaseAdapter):
        def get_sync_uri(self) -> str:
            return "custom://sync"
        
        def get_async_uri(self) -> str:
            return "custom://async"
        
        def create_engine(self, echo: bool = False):
            return None
        
        def get_metadata_kwargs(self) -> dict:
            return {}
        
        def supports_schemas(self) -> bool:
            return False
        
        def get_session_setup_sql(self) -> str | None:
            return None
    
    # Register custom adapter
    DatabaseAdapterFactory.register_adapter("custom", CustomAdapter)
    
    # Create instance
    adapter = DatabaseAdapterFactory.create("custom")
    assert isinstance(adapter, CustomAdapter)
    assert adapter.get_sync_uri() == "custom://sync"
    assert adapter.get_async_uri() == "custom://async"


def test_adapter_engine_creation():
    """Test that adapters can create SQLAlchemy engines."""
    adapter = DatabaseAdapterFactory.create("sqlite", db_path=":memory:")
    engine = adapter.create_engine(echo=False)
    
    # Verify engine was created
    assert engine is not None
    assert hasattr(engine, "url")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
