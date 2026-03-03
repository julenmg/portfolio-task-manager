"""RBAC integration tests.

Covers:
- Unauthenticated requests → 401
- Wrong role → 403
- Account owner (Customer) → 200
- BankTeller → 200 for any account
- Admin → 200 for any account
- Customer cannot transfer from another user's account → 403
"""

from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.domain.bank.models import BankAccount
from app.models.user import Role, User


def _token(user: User) -> str:
    return create_access_token(user.id, user.role.value)


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user)}"}


# ── GET /bank/accounts/{id}/transactions ────────────────────────────────────


@pytest.mark.asyncio
async def test_get_transactions_no_token(
    client: AsyncClient,
    checking_account: BankAccount,
) -> None:
    resp = await client.get(f"/api/v1/bank/accounts/{checking_account.id}/transactions")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_transactions_owner_allowed(
    client: AsyncClient,
    checking_account: BankAccount,
    customer_user: User,
) -> None:
    resp = await client.get(
        f"/api/v1/bank/accounts/{checking_account.id}/transactions",
        headers=_auth(customer_user),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_transactions_other_customer_denied(
    client: AsyncClient,
    checking_account: BankAccount,
    teller_user: User,
    db_session,
) -> None:
    """A Customer whose ID doesn't match the account owner gets 403."""
    from app.models.user import Role
    from app.repositories.user_repository import UserRepository
    import bcrypt

    # Create a second customer (not the owner of checking_account)
    other = await UserRepository(db_session).create(
        email="other@example.com",
        username="other_customer",
        hashed_password=bcrypt.hashpw(b"secret", bcrypt.gensalt()).decode(),
    )
    other.role = Role.CUSTOMER
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/bank/accounts/{checking_account.id}/transactions",
        headers=_auth(other),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_transactions_teller_allowed(
    client: AsyncClient,
    checking_account: BankAccount,
    teller_user: User,
) -> None:
    resp = await client.get(
        f"/api/v1/bank/accounts/{checking_account.id}/transactions",
        headers=_auth(teller_user),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_transactions_admin_allowed(
    client: AsyncClient,
    checking_account: BankAccount,
    admin_user: User,
) -> None:
    resp = await client.get(
        f"/api/v1/bank/accounts/{checking_account.id}/transactions",
        headers=_auth(admin_user),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_transactions_account_not_found(
    client: AsyncClient,
    admin_user: User,
) -> None:
    resp = await client.get(
        "/api/v1/bank/accounts/99999/transactions",
        headers=_auth(admin_user),
    )
    assert resp.status_code == 404


# ── POST /bank/transfers ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_transfer_no_token(
    client: AsyncClient,
    checking_account: BankAccount,
    second_checking_account: BankAccount,
) -> None:
    resp = await client.post(
        "/api/v1/bank/transfers",
        json={
            "from_account_id": checking_account.id,
            "to_account_id": second_checking_account.id,
            "amount": "100.00",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_transfer_customer_own_account_allowed(
    client: AsyncClient,
    checking_account: BankAccount,
    second_checking_account: BankAccount,
    customer_user: User,
) -> None:
    """Customer transferring FROM their own account → allowed."""
    resp = await client.post(
        "/api/v1/bank/transfers",
        json={
            "from_account_id": checking_account.id,
            "to_account_id": second_checking_account.id,
            "amount": "50.00",
        },
        headers=_auth(customer_user),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_transfer_customer_other_account_denied(
    client: AsyncClient,
    checking_account: BankAccount,
    second_checking_account: BankAccount,
    customer_user: User,
) -> None:
    """Customer transferring FROM someone else's account → 403."""
    resp = await client.post(
        "/api/v1/bank/transfers",
        json={
            "from_account_id": second_checking_account.id,  # owned by teller_user
            "to_account_id": checking_account.id,
            "amount": "50.00",
        },
        headers=_auth(customer_user),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_transfer_teller_any_account_allowed(
    client: AsyncClient,
    checking_account: BankAccount,
    second_checking_account: BankAccount,
    teller_user: User,
) -> None:
    resp = await client.post(
        "/api/v1/bank/transfers",
        json={
            "from_account_id": checking_account.id,
            "to_account_id": second_checking_account.id,
            "amount": "50.00",
        },
        headers=_auth(teller_user),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_transfer_admin_any_account_allowed(
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
            "amount": "50.00",
        },
        headers=_auth(admin_user),
    )
    assert resp.status_code == 200


# ── POST /bank/accounts ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_account_customer_denied(
    client: AsyncClient,
    customer_user: User,
) -> None:
    resp = await client.post(
        "/api/v1/bank/accounts",
        json={"user_id": customer_user.id, "account_type": "checking"},
        headers=_auth(customer_user),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_account_teller_allowed(
    client: AsyncClient,
    teller_user: User,
) -> None:
    resp = await client.post(
        "/api/v1/bank/accounts",
        json={"user_id": teller_user.id, "account_type": "checking"},
        headers=_auth(teller_user),
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_account_admin_allowed(
    client: AsyncClient,
    admin_user: User,
) -> None:
    resp = await client.post(
        "/api/v1/bank/accounts",
        json={"user_id": admin_user.id, "account_type": "savings"},
        headers=_auth(admin_user),
    )
    assert resp.status_code == 201


# ── GET /bank/accounts (list) ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_accounts_no_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/bank/accounts")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_accounts_customer_sees_own(
    client: AsyncClient,
    checking_account,
    customer_user: User,
) -> None:
    resp = await client.get("/api/v1/bank/accounts", headers=_auth(customer_user))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert all(a["user_id"] == customer_user.id for a in data)


@pytest.mark.asyncio
async def test_list_accounts_admin_sees_all(
    client: AsyncClient,
    checking_account,
    second_checking_account,
    admin_user: User,
) -> None:
    resp = await client.get("/api/v1/bank/accounts", headers=_auth(admin_user))
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


# ── GET /bank/accounts/{id} ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_account_owner_allowed(
    client: AsyncClient,
    checking_account,
    customer_user: User,
) -> None:
    resp = await client.get(
        f"/api/v1/bank/accounts/{checking_account.id}",
        headers=_auth(customer_user),
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == checking_account.id


@pytest.mark.asyncio
async def test_get_account_other_customer_denied(
    client: AsyncClient,
    second_checking_account,
    customer_user: User,
) -> None:
    """Customer cannot view an account belonging to another user."""
    resp = await client.get(
        f"/api/v1/bank/accounts/{second_checking_account.id}",
        headers=_auth(customer_user),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_account_teller_allowed(
    client: AsyncClient,
    checking_account,
    teller_user: User,
) -> None:
    resp = await client.get(
        f"/api/v1/bank/accounts/{checking_account.id}",
        headers=_auth(teller_user),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_account_not_found(
    client: AsyncClient,
    admin_user: User,
) -> None:
    resp = await client.get("/api/v1/bank/accounts/99999", headers=_auth(admin_user))
    assert resp.status_code == 404


# ── GET /audit/logs ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_logs_admin_allowed(
    client: AsyncClient,
    admin_user: User,
) -> None:
    resp = await client.get("/api/v1/audit/logs", headers=_auth(admin_user))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_audit_logs_customer_denied(
    client: AsyncClient,
    customer_user: User,
) -> None:
    resp = await client.get("/api/v1/audit/logs", headers=_auth(customer_user))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_logs_teller_denied(
    client: AsyncClient,
    teller_user: User,
) -> None:
    resp = await client.get("/api/v1/audit/logs", headers=_auth(teller_user))
    assert resp.status_code == 403
