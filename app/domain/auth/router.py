import bcrypt

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.domain.auth.schemas import TokenResponse
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email (passed as ``username``) and password.

    Returns a Bearer JWT that embeds the user's role.
    The token is valid for 60 minutes.
    """
    # OAuth2PasswordRequestForm uses "username" field — we treat it as email.
    user = await UserRepository(db).get_by_email(form.username)

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None or not bcrypt.checkpw(
        form.password.encode(), user.hashed_password.encode()
    ):
        raise invalid_credentials

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    token = create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=token, token_type="bearer", role=user.role.value)
