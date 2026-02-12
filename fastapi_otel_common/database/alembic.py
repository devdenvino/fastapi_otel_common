"""Alembic migration utilities for multi-tenant, schema-per-tenant support.

Runs migrations in both offline and online modes, using PostgreSQL
search_path to target the current tenant schema. Migration scripts
remain schemaless (no explicit `schema=`).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text
from sqlalchemy.schema import MetaData

from .db import SQLALCHEMY_DATABASE_URI_SYNC

# Alembic Config object, provides access to the .ini file values.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_tenant() -> str | None:
    """Read current tenant from -x tenant=... arguments."""
    return context.get_x_argument(as_dictionary=True).get("tenant")


def run_migrations_offline(target_metadata: MetaData) -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    No schema qualifiers are emitted; the active schema must be
    controlled by the database URL / search_path externally.

    Args:
        target_metadata: SQLAlchemy MetaData object (ideally without schema=).
    """
    url = config.get_main_option("sqlalchemy.url")

    # In schemaless mode, we do NOT pass version_table_schema or include_schemas.
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        # Do not emit CREATE SCHEMA or SET search_path here; offline mode
        # should be backend-agnostic and just produce SQL.
        context.run_migrations()


def run_migrations_online(target_metadata: MetaData) -> None:
    """Run migrations in 'online' mode.

    Uses PostgreSQL search_path to point all operations at the
    requested tenant schema. Migration scripts are generated and
    executed without schema qualifiers.

    Args:
        target_metadata: SQLAlchemy MetaData object (ideally without schema=).
    """
    current_tenant = get_tenant()

    alembic_config = config.get_section(config.config_ini_section, {}) or {}
    alembic_config["sqlalchemy.url"] = SQLALCHEMY_DATABASE_URI_SYNC
    print(f"Connecting to {alembic_config['sqlalchemy.url']}")

    connectable = engine_from_config(
        alembic_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Only do tenant-specific work for PostgreSQL and when a tenant is given.
        if connection.dialect.name == "postgresql" and current_tenant:
            # Ensure tenant schema exists.
            connection.execute(
                text(f'CREATE SCHEMA IF NOT EXISTS "{current_tenant.replace("\"", "\"\"")}"')
            )

            # Set search_path so all CREATE/ALTER/DROP target this schema by default.
            connection.execute(
                text(f'set search_path to "{current_tenant.replace("\"", "\"\"")}"')
            )
            # In SQLAlchemy v2+ the search path change needs to be committed.
            connection.commit()

            # Make the dialect reflect tables in terms of the current tenant.
            connection.dialect.default_schema_name = current_tenant

        # Schemaless Alembic configuration: no include_schemas, no version_table_schema.
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()
