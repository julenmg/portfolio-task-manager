"""Tests for the AuditMiddleware.

Verifies that 401 and 403 responses generate rows in the audit_logs table
and that successful requests do not.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.audit_log import AuditLog
from app.models.user import Role, User
from app.repositories.audit_repository import AuditLogRepository


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.role.value)
    return {"Authorization": f"Bearer {token}"}


async def _audit_count(db: AsyncSession) -> int:
    logs = await AuditLogRepository(db).get_recent(limit=1000)
    return len(logs)


@pytest.mark.asyncio
async def test_401_creates_audit_log(
    client: AsyncClient,
    db_session: AsyncSession,
    checking_account,
) -> None:
    """Unauthenticated request → 401 → one audit log entry."""
    before = await _audit_count(db_session)
    resp = await client.get(
        f"/api/v1/bank/accounts/{checking_account.id}/transactions"
    )
    assert resp.status_code == 401

    # The middleware writes its own session; give SQLite StaticPool a moment
    # to flush (it's synchronous under the hood so a second query is enough).
    after = await _audit_count(db_session)
    assert after == before + 1


@pytest.mark.asyncio
async def test_403_creates_audit_log(
    client: AsyncClient,
    db_session: AsyncSession,
    checking_account,
    customer_user: User,
) -> None:
    """Customer trying to access audit logs → 403 → one audit log entry."""
    before = await _audit_count(db_session)
    resp = await client.get("/api/v1/audit/logs", headers=_auth(customer_user))
    assert resp.status_code == 403

    after = await _audit_count(db_session)
    assert after == before + 1


@pytest.mark.asyncio
async def test_successful_request_no_audit_log(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_user: User,
) -> None:
    """Successful request (200) should NOT create an audit log entry."""
    before = await _audit_count(db_session)
    resp = await client.get("/api/v1/audit/logs", headers=_auth(admin_user))
    assert resp.status_code == 200

    after = await _audit_count(db_session)
    assert after == before


@pytest.mark.asyncio
async def test_audit_log_fields(
    client: AsyncClient,
    db_session: AsyncSession,
    checking_account,
) -> None:
    """Audit log entry has the correct method, path, and status_code."""
    await client.get(f"/api/v1/bank/accounts/{checking_account.id}/transactions")

    logs = await AuditLogRepository(db_session).get_recent(limit=10)
    assert len(logs) >= 1
    entry: AuditLog = logs[0]

    assert entry.method == "GET"
    assert entry.path == f"/api/v1/bank/accounts/{checking_account.id}/transactions"
    assert entry.status_code == 401
    assert "Unauthenticated" in (entry.reason or "")


@pytest.mark.asyncio
async def test_403_audit_log_reason(
    client: AsyncClient,
    db_session: AsyncSession,
    customer_user: User,
) -> None:
    """403 audit log entry contains the 'Unauthorized' reason."""
    await client.get("/api/v1/audit/logs", headers=_auth(customer_user))

    logs = await AuditLogRepository(db_session).get_recent(limit=10)
    entry = next((l for l in logs if l.status_code == 403), None)
    assert entry is not None
    assert "Unauthorized" in (entry.reason or "")


@pytest.mark.asyncio
async def test_audit_log_user_id_populated_on_403(
    client: AsyncClient,
    db_session: AsyncSession,
    customer_user: User,
) -> None:
    """When the user is identified but lacks the required role, user_id is recorded."""
    await client.get("/api/v1/audit/logs", headers=_auth(customer_user))

    logs = await AuditLogRepository(db_session).get_recent(limit=10)
    entry = next((l for l in logs if l.status_code == 403), None)
    assert entry is not None
    assert entry.user_id == customer_user.id


@pytest.mark.asyncio
async def test_audit_log_user_id_none_on_401(
    client: AsyncClient,
    db_session: AsyncSession,
    checking_account,
) -> None:
    """When no valid token is supplied, user_id in the audit log is None."""
    await client.get(f"/api/v1/bank/accounts/{checking_account.id}/transactions")

    logs = await AuditLogRepository(db_session).get_recent(limit=10)
    entry = next((l for l in logs if l.status_code == 401), None)
    assert entry is not None
    assert entry.user_id is None
