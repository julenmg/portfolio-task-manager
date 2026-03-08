"""Unit and integration tests for the login rate limiter."""

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.middleware.rate_limit import _buckets, _check, login_rate_limit


# ── Unit tests: sliding-window counter ───────────────────────────────────────

def _fresh_key() -> str:
    """Return a unique key so each test gets its own bucket."""
    import uuid
    return f"test-{uuid.uuid4()}"


def test_check_allows_requests_within_limit():
    key = _fresh_key()
    for _ in range(5):
        assert _check(key, max_requests=5, window=60) is True


def test_check_blocks_when_limit_reached():
    key = _fresh_key()
    for _ in range(5):
        _check(key, max_requests=5, window=60)
    assert _check(key, max_requests=5, window=60) is False


def test_check_evicts_expired_entries():
    """Entries older than the window must not count toward the limit."""
    import time
    key = _fresh_key()
    # Pre-fill with entries that are already expired (window=0)
    _buckets[key] = [time.monotonic() - 10]
    # With a 1-second window those timestamps are expired → request should be allowed
    assert _check(key, max_requests=1, window=1) is True


# ── Integration test: rate-limited login endpoint ─────────────────────────────

@pytest.mark.asyncio
async def test_login_rate_limit_returns_429():
    """The login endpoint must return 429 after exceeding the limit.

    We use a dedicated client WITHOUT the rate-limit dependency override
    so the real limiter is exercised.
    """
    from app.core.database import Base, get_db
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    # Deliberately do NOT override login_rate_limit

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://ratelimitip") as ac:
        # Use a form payload — no real user needed; we just want to trigger rate limiting
        responses = []
        for _ in range(12):  # more than _LOGIN_MAX (10)
            r = await ac.post(
                "/api/v1/auth/login",
                data={"username": "nobody@test.com", "password": "WrongPass1"},
            )
            responses.append(r.status_code)

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(login_rate_limit, None)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # At least one response must be 429
    assert 429 in responses
