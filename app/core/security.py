"""JWT creation and verification.

Kept intentionally thin — no ORM imports, no FastAPI imports.
This module is imported by the auth dependencies and the audit middleware.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(user_id: int, role: str) -> str:
    """Return a signed JWT embedding the user's ID and role."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT.  Raises ``JWTError`` on failure."""
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


def extract_user_id_from_header(authorization: str) -> int | None:
    """Best-effort extraction of user_id from an Authorization header.

    Used by the audit middleware where no DB call is desired.
    Returns ``None`` on any failure (expired, malformed, missing).
    """
    if not authorization.startswith("Bearer "):
        return None
    try:
        payload = decode_token(authorization[7:])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError, TypeError):
        return None
