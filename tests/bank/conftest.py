from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bank.models import BankAccount
from app.domain.bank.repository import AccountRepository


async def _make_account(
    db_session: AsyncSession,
    *,
    account_number: str,
    account_type: str,
    balance: Decimal = Decimal("0.00"),
    interest_rate: Decimal = Decimal("0.000000"),
    is_active: bool = True,
) -> BankAccount:
    repo = AccountRepository(db_session)
    account = await repo.create(
        user_id=1,
        account_number=account_number,
        account_type=account_type,
        interest_rate=interest_rate,
    )
    account.balance = balance
    account.is_active = is_active
    await db_session.flush()
    return account


@pytest.fixture
async def checking_account(db_session: AsyncSession) -> BankAccount:
    return await _make_account(
        db_session,
        account_number="ACC000000000001",
        account_type="checking",
        balance=Decimal("1000.00"),
    )


@pytest.fixture
async def second_checking_account(db_session: AsyncSession) -> BankAccount:
    return await _make_account(
        db_session,
        account_number="ACC000000000002",
        account_type="checking",
        balance=Decimal("500.00"),
    )


@pytest.fixture
async def savings_account(db_session: AsyncSession) -> BankAccount:
    return await _make_account(
        db_session,
        account_number="ACC000000000003",
        account_type="savings",
        balance=Decimal("5000.00"),
        interest_rate=Decimal("0.05"),  # 5 % annual
    )


@pytest.fixture
async def inactive_account(db_session: AsyncSession) -> BankAccount:
    return await _make_account(
        db_session,
        account_number="ACC000000000004",
        account_type="checking",
        balance=Decimal("200.00"),
        is_active=False,
    )
