from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a DB session with explicit transaction management.

    Uses ``begin()`` so that:
    - The transaction is started explicitly (BEGIN).
    - On a clean request exit the session auto-commits (COMMIT).
    - On any unhandled exception the session auto-rolls back (ROLLBACK).

    Routers that use this dependency must NOT call ``session.commit()``
    themselves — the context manager does it automatically.
    """
    async with AsyncSessionLocal.begin() as session:
        yield session
