"""
SQLAlchemy async database engine and session management for Numeris.
Uses aiosqlite as the async driver for SQLite.
Numeris v3.0
"""

from __future__ import annotations

import contextlib
from typing import Any, AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from backend.core.config import settings
from backend.utils.logger import get_logger

logger = get_logger("database")


# ---------------------------------------------------------------------------
# Declarative base (shared by all ORM models)
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """SQLAlchemy declarative base — all models inherit from this."""
    pass


# ---------------------------------------------------------------------------
# Engine + session factory (created lazily)
# ---------------------------------------------------------------------------
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def _build_db_url() -> str:
    path = settings.SQLITE_DB_PATH
    return f"sqlite+aiosqlite:///{path}"


def get_engine() -> AsyncEngine:
    """Return (or create) the shared async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        db_url = _build_db_url()
        _engine = create_async_engine(
            db_url,
            echo=settings.APP_ENV == "development",
            connect_args={"check_same_thread": False, "timeout": 30},
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        logger.info("Database engine created", extra={"url": db_url})
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return (or create) the async session factory."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )
        logger.info("Async session factory created")
    return _session_factory


async def init_db() -> None:
    """Create all tables on startup."""
    engine = get_engine()
    async with engine.begin() as conn:
        # Import all models here to ensure they are registered with Base
        # noinspection PyUnresolvedReferences
        from backend.db import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


@contextlib.asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.
    Usage:
        async with get_db_session() as session:
            # use session
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async session.
    """
    async with get_db_session() as session:
        yield session


async def execute_query(query: str, params: dict = None) -> list[dict]:
    """
    Raw query executor.
    Args:
        query: SQL query string
        params: Dictionary of parameters (optional)
    Returns:
        List of dictionaries representing the rows
    """
    params = params or {}
    async with get_db_session() as session:
        result = await session.execute(text(query), params)
        # Convert to list of dicts
        return [dict(row) for row in result.fetchall()]


# ---------------------------------------------------------------------------
# Alembic integration: env.py configuration comments included
# ---------------------------------------------------------------------------
# The following is typically placed in alembic/env.py:
#
# from logging.config import fileConfig
# from sqlalchemy import engine_from_config
# from sqlalchemy import pool
# from alembic import context
# from backend.db.database import Base
#
# # this is the Alembic Config object, which provides
# # access to the values within the .ini file in use.
# config = context.config
#
# # Interpret the config file for Python logging.
# # This line sets up loggers basically.
# if config.config_file_name is not None:
#     fileConfig(config.config_file_name)
#
# # add your model's MetaData object here
# # for 'autogenerate' support
# target_metadata = Base.metadata
#
# # other values from the config, defined by the needs of env.py,
# # can be acquired:
# # my_important_option = config.get_main_option("my_important_option")
# # ... etc.
#
#
# def run_migrations_offline():
#     """Run migrations in 'offline' mode.
#     This configures the context with just a URL
#     and not an Engine, though an Engine is acceptable
#     here as well.  By skipping the Engine creation
#     we don't even need a DBAPI to be available.
#     """
#     url = config.get_main_option("sqlalchemy.url")
#     context.configure(
#         url=url,
#         target_metadata=target_metadata,
#         literal_binds=True,
#         dialect_opts={"paramstyle": "named"},
#     )
#
#     with context.begin_transaction():
#         context.run_migrations()
#
#
# def run_migrations_online():
#     """Run migrations in 'online' mode.
#     In this scenario we need to create an Engine
#     and associate a connection with the context.
#     """
#     # this is the Alembic Config object, which provides
#     # access to the values within the .ini file in use.
#     config = context.config
#
#     # Interpret the config file for Python logging.
#     # This line sets up loggers basically.
#     if config.config_file_name is not None:
#         fileConfig(config.config_file_name)
#
#     # add your model's MetaData object here
#     # for 'autogenerate' support
#     target_metadata = Base.metadata
#
#     # this is the SQLAlchemy engine
#     # that will be used to run the migrations.
#     connectable = engine_from_config(
#         config.get_section(config.config_ini_section),
#         prefix="sqlalchemy.",
#         poolclass=pool.NullPool,
#     )
#
#     with connectable.connect() as connection:
#         context.configure(
#             connection=connection, target_metadata=target_metadata
#         )
#
#         with context.begin_transaction():
#             context.run_migrations()
#
#     if context.is_offline_mode():
#         run_migrations_offline()
#     else:
#         run_migrations_online()
