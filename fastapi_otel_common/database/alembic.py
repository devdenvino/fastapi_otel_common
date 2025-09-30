from alembic import context
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from .db import SQLALCHEMY_DATABASE_URI_SYNC


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline(target_metadata) -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        version_table_schema=target_metadata.schema,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        print(f"Creating schema {target_metadata.schema} if not exists")
        context.execute(
            f"create schema if not exists {target_metadata.schema};")
        context.execute(f"set search_path to {target_metadata.schema}")
        context.run_migrations()


def run_migrations_online(target_metadata) -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    current_tenant = context.get_x_argument(as_dictionary=True).get("tenant")

    alembic_config = config.get_section(config.config_ini_section, {})
    alembic_config["sqlalchemy.url"] = SQLALCHEMY_DATABASE_URI_SYNC
    print(f"Connecting to {alembic_config['sqlalchemy.url']}")
    connectable = engine_from_config(
        alembic_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # set search path on the connection, which ensures that
        # PostgreSQL will emit all CREATE / ALTER / DROP statements
        # in terms of this schema by default
        connection.execute(text('set search_path to "%s"' % current_tenant))
        # in SQLAlchemy v2+ the search path change needs to be committed
        connection.commit()

        # make use of non-supported SQLAlchemy attribute to ensure
        # the dialect reflects tables in terms of the current tenant name
        connection.dialect.default_schema_name = current_tenant

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=False,
        )

        with context.begin_transaction():
            if target_metadata.schema is not None and target_metadata.schema != "":
                print(
                    f"Creating schema {target_metadata.schema} if not exists")
                context.execute(
                    f"create schema if not exists {target_metadata.schema};"
                )
                context.execute(f"set search_path to {target_metadata.schema}")
            context.run_migrations()
