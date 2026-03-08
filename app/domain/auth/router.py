import hmac

import bcrypt

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.domain.auth.schemas import TokenResponse
from app.middleware.rate_limit import login_rate_limit
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])

# Dummy hash used to keep response time constant when the user does not exist,
# preventing timing-based account enumeration.
_DUMMY_HASH = bcrypt.hashpw(b"dummy", bcrypt.gensalt()).decode()


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(login_rate_limit),
) -> TokenResponse:
    """Authenticate with email (passed as ``username``) and password.

    Returns a Bearer JWT that embeds the user's role.
    The token is valid for 60 minutes.

    Security measures:
    - Constant-time password check (bcrypt always runs, even for unknown emails).
    - Rate-limited to 10 attempts per IP per 60 s.
    - Inactive accounts return 403 after credential verification.
    """
    # OAuth2PasswordRequestForm uses "username" field — we treat it as email.
    user = await UserRepository(db).get_by_email(form.username)

    # Always run bcrypt regardless of whether the user exists so that
    # response timing does not reveal valid email addresses.
    candidate_hash = user.hashed_password if user is not None else _DUMMY_HASH
    password_ok = bcrypt.checkpw(form.password.encode(), candidate_hash.encode())

    if user is None or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    token = create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=token, token_type="bearer", role=user.role.value)
