"""FastAPI dependencies for authentication and role-based access control.

Usage examples
──────────────
# Any authenticated user
current_user: User = Depends(get_current_user)

# Only Admin
admin: User = Depends(require_roles(Role.ADMIN))

# BankTeller OR Admin
staff: User = Depends(require_roles(Role.BANK_TELLER, Role.ADMIN))
"""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import Role, User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate the Bearer JWT and return the active user from the database.

    Using the DB role (not the token role) for every authorization decision
    ensures that role changes take effect without waiting for token expiry.
    """
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise exc

    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise exc
    return user


def require_roles(*roles: Role) -> Callable:
    """Dependency factory: allow only users whose role is in ``roles``."""

    async def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {' or '.join(r.value for r in roles)}",
            )
        return current_user

    return _guard
