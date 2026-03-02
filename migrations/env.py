"""Alembic environment with async SQLAlchemy support.

Both offline and online modes are provided:
- Offline: generates SQL script (no live DB connection required).
- Online:  connects via asyncpg, runs migrations inside an explicit
           BEGIN … COMMIT block courtesy of ``context.begin_transaction()``.

All migration scripts run inside a single database transaction, so a
failed migration is automatically rolled back and the schema remains
consistent.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# Register all ORM models so that autogenerate can compare them against the
# current database schema.
# ---------------------------------------------------------------------------
import app.models  # noqa: F401 — registers User
import app.domain.bank.models  # noqa: F401 — registers BankAccount, Transaction, Transfer

from app.core.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline mode — emit raw SQL to stdout (useful for DBAs / CI review)
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """Generate SQL without connecting to a live database.

    Each migration is wrapped in an explicit BEGIN … COMMIT block so that
    DBAs can see exactly what transaction boundaries are used.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Emit one transaction per migration file.
        transaction_per_migration=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online async mode — connect via asyncpg and run inside a transaction
# ---------------------------------------------------------------------------

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Emit one transaction per migration file (each gets its own
        # BEGIN … COMMIT; a failure rolls back only that migration).
        transaction_per_migration=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and drive migrations synchronously inside it."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # run_sync lets us call the synchronous Alembic API from async context.
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
