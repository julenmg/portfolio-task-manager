"""Integration tests for POST /users/register and related error paths."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/users/register",
        json={"email": "new@example.com", "username": "newuser", "password": "pass1234"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert body["username"] == "newuser"
    assert "id" in body
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, db_session: AsyncSession) -> None:
    await UserRepository(db_session).create(
        email="dup@example.com", username="dupuser", hashed_password="hashed"
    )
    await db_session.flush()

    resp = await client.post(
        "/api/v1/users/register",
        json={"email": "dup@example.com", "username": "anotheruser", "password": "pass1234"},
    )
    assert resp.status_code == 409
    assert "Email" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, db_session: AsyncSession) -> None:
    await UserRepository(db_session).create(
        email="unique@example.com", username="takenname", hashed_password="hashed"
    )
    await db_session.flush()

    resp = await client.post(
        "/api/v1/users/register",
        json={"email": "other@example.com", "username": "takenname", "password": "pass1234"},
    )
    assert resp.status_code == 409
    assert "Username" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/users/register",
        json={"email": "not-an-email", "username": "validuser", "password": "pass1234"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_password_too_short(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/users/register",
        json={"email": "short@example.com", "username": "shortpass", "password": "abc"},
    )
    assert resp.status_code == 422
