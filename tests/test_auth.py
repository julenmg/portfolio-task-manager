"""Integration tests for the /auth/login endpoint."""

import bcrypt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Role, User
from app.repositories.user_repository import UserRepository


async def _create_user(
    db: AsyncSession,
    *,
    email: str = "user@example.com",
    username: str = "testuser",
    password: str = "password123",
    role: Role = Role.CUSTOMER,
) -> User:
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = await UserRepository(db).create(
        email=email, username=username, hashed_password=hashed
    )
    user.role = role
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession) -> None:
    """Valid credentials return a token and the user's role."""
    await _create_user(db_session, email="auth@example.com", username="authuser")

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "auth@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["role"] == Role.CUSTOMER.value


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_user(db_session, email="bad@example.com", username="baduser")

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "bad@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@example.com", "password": "password123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_admin_role(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_user(
        db_session,
        email="admin@example.com",
        username="adminuser",
        role=Role.ADMIN,
    )
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "password123"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == Role.ADMIN.value
