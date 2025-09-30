import sys
import os

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from alembic import command
from alembic.config import Config

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (AsyncAttrs, AsyncSession,
                                    create_async_engine)
from sqlalchemy.orm import declarative_base, sessionmaker

from ..core.config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_POOL_RECYCLE, DB_POOL_SIZE, DB_POOL_TIMEOUT, DB_SCHEMA, DB_USER, DB_MAX_OVERFLOW, ECHO_SQL
from ..logging.logger import get_logger

logger = get_logger(__name__)

SQLALCHEMY_DATABASE_URI_SYNC = (
    f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

SQLALCHEMY_DATABASE_URI = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URI,
    echo=ECHO_SQL,
    future=True,
    query_cache_size=100,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_timeout=DB_POOL_TIMEOUT,
)

AsyncSessionLocal = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession)


# base class for creating database models


if "alembic" not in sys.argv[0]:
    Base = declarative_base(metadata=MetaData(
        schema=DB_SCHEMA), cls=AsyncAttrs)
else:
    Base = declarative_base(cls=AsyncAttrs)


class BaseModel(Base):
    __abstract__ = True

    def to_json(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def from_json(cls, json_data):
        return cls(**json_data)


async def init_models():
    """
    Initialize database models.
    If INIT_DB environment variable is 'true', it drops and creates all tables.
    This is a destructive operation and should only be used in development/testing.
    """
    if os.getenv("INIT_DB") == "true":
        logger.info("Initializing DB...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Initialized DB.")
    else:
        logger.info("Skipping DB initialization. Using existing DB.")
        pass


# Dependency to get DB session
@asynccontextmanager
async def get_db_session_with_async_context() -> AsyncGenerator[AsyncSession, None]:
    logger.info(f"Getting DB session...")
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("SET search_path TO {};".format(DB_SCHEMA)))
            await session.commit()
            logger.info(
                "Got DB session with search path {}.".format(DB_SCHEMA))
            yield session
        finally:
            logger.debug("DB session closed.")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get an async database session."""
    logger.info(f"Getting DB session...")

    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("SET search_path TO {};".format(DB_SCHEMA)))
            await session.commit()
            logger.info(
                "Got DB session with search path {}.".format(DB_SCHEMA))
            yield session
        finally:
            logger.debug("DB session closed.")


@asynccontextmanager
async def close_db_connection():
    """Closes the database connection engine."""
    logger.info("Closing DB connection...")
    await engine.dispose()
    logger.info("Closed DB connection.")


# Function to apply migrations
def apply_migrations():
    """Applies alembic migrations to the database."""
    logger.info("Applying database migrations...")
    try:
        alembic_cfg = Config("alembic.ini")
        # alembic_cfg.set_main_option(
        #     "sqlalchemy.url", SQLALCHEMY_DATABASE_URI_SYNC)
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully.")
    except Exception as e:
        logger.error("Error applying migrations: %s", e)
        raise
