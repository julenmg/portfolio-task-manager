"""Sliding-window in-memory rate limiter (no external dependencies).

Usage as a FastAPI dependency
------------------------------
    from app.middleware.rate_limit import login_rate_limit

    @router.post("/login")
    async def login(
        _: None = Depends(login_rate_limit),
        ...
    ):
        ...

Tests override the dependency via app.dependency_overrides so that
rate-limit state does not interfere with test isolation.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

# { client_ip: [timestamp, ...] }
_buckets: dict[str, list[float]] = defaultdict(list)

_LOGIN_MAX = 10       # requests
_LOGIN_WINDOW = 60    # seconds


def _check(key: str, *, max_requests: int, window: int) -> bool:
    """Return True if allowed, False if rate-limited (side-effect: records attempt)."""
    now = time.monotonic()
    cutoff = now - window
    bucket = _buckets[key]
    _buckets[key] = [t for t in bucket if t > cutoff]
    if len(_buckets[key]) >= max_requests:
        return False
    _buckets[key].append(now)
    return True


async def login_rate_limit(request: Request) -> None:
    """Allow max 10 login attempts per IP per 60 s.

    Tests override this dependency to a no-op via app.dependency_overrides.
    """
    ip = request.client.host if request.client else "unknown"
    if not _check(ip, max_requests=_LOGIN_MAX, window=_LOGIN_WINDOW):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again in 60 seconds.",
            headers={"Retry-After": "60"},
        )
