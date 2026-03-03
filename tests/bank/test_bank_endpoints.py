"""Integration tests for bank HTTP endpoints — error paths and edge cases."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.domain.bank.models import BankAccount
from app.models.user import User


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


# ── POST /bank/transfers — HTTP error paths ───────────────────────────────────


@pytest.mark.asyncio
async def test_transfer_account_not_found_returns_404(
    client: AsyncClient,
    checking_account: BankAccount,
    admin_user: User,
) -> None:
    resp = await client.post(
        "/api/v1/bank/transfers",
        json={
            "from_account_id": checking_account.id,
            "to_account_id": 99999,
            "amount": "10.00",
        },
        headers=_auth(admin_user),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_transfer_inactive_account_returns_404(
    client: AsyncClient,
    checking_account: BankAccount,
    inactive_account: BankAccount,
    admin_user: User,
) -> None:
    resp = await client.post(
        "/api/v1/bank/transfers",
        json={
            "from_account_id": checking_account.id,
            "to_account_id": inactive_account.id,
            "amount": "10.00",
        },
        headers=_auth(admin_user),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_transfer_insufficient_funds_returns_422(
    client: AsyncClient,
    checking_account: BankAccount,
    second_checking_account: BankAccount,
    admin_user: User,
) -> None:
    resp = await client.post(
        "/api/v1/bank/transfers",
        json={
            "from_account_id": checking_account.id,
            "to_account_id": second_checking_account.id,
            "amount": "999999.00",
        },
        headers=_auth(admin_user),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_transfer_same_account_returns_400(
    client: AsyncClient,
    checking_account: BankAccount,
    admin_user: User,
) -> None:
    resp = await client.post(
        "/api/v1/bank/transfers",
        json={
            "from_account_id": checking_account.id,
            "to_account_id": checking_account.id,
            "amount": "10.00",
        },
        headers=_auth(admin_user),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_transfer_customer_account_not_found_returns_403(
    client: AsyncClient,
    customer_user: User,
) -> None:
    """Customer: from_account doesn't exist → 403 (ownership check fails)."""
    resp = await client.post(
        "/api/v1/bank/transfers",
        json={
            "from_account_id": 99999,
            "to_account_id": 99998,
            "amount": "10.00",
        },
        headers=_auth(customer_user),
    )
    assert resp.status_code == 403


# ── GET /bank/accounts (list) — teller branch ────────────────────────────────


@pytest.mark.asyncio
async def test_list_accounts_teller_sees_all(
    client: AsyncClient,
    checking_account: BankAccount,
    second_checking_account: BankAccount,
    teller_user: User,
) -> None:
    resp = await client.get("/api/v1/bank/accounts", headers=_auth(teller_user))
    assert resp.status_code == 200
    assert len(resp.json()) >= 2
