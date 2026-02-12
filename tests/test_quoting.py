
import pytest
from sqlalchemy import text
from fastapi_otel_common.database.adapters import PostgreSQLAdapter

@pytest.mark.asyncio
async def test_postgresql_adapter_quoting():
    # Test with a schema that needs quoting (e.g. contains a dash)
    adapter = PostgreSQLAdapter(
        user="user",
        password="password",
        host="localhost",
        port="5432",
        database="db",
        schema="my-schema"
    )
    
    # Check session setup SQL
    sql = adapter.get_session_setup_sql()
    assert sql == 'SET search_path TO "my-schema";'

    # Test with a schema that contains a double quote (injection attempt)
    adapter_injection = PostgreSQLAdapter(
        user="user",
        password="password",
        host="localhost",
        port="5432",
        database="db",
        schema='my"schema'
    )
    
    # Check session setup SQL - should escape double quotes
    sql_injection = adapter_injection.get_session_setup_sql()
    assert sql_injection == 'SET search_path TO "my""schema";'
