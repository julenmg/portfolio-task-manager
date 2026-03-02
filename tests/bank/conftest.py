from decimal import Decimal

import bcrypt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bank.models import BankAccount
from app.domain.bank.repository import AccountRepository
from app.models.user import Role, User
from app.repositories.user_repository import UserRepository


# ── helpers ────────────────────────────────────────────────────────────────


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def _make_user(
    db: AsyncSession,
    *,
    email: str,
    username: str,
    role: Role,
    password: str = "secret",
) -> User:
    repo = UserRepository(db)
    return await repo.create(
        email=email,
        username=username,
        hashed_password=_hash(password),
    )


async def _make_account(
    db_session: AsyncSession,
    *,
    user_id: int,
    account_number: str,
    account_type: str,
    balance: Decimal = Decimal("0.00"),
    interest_rate: Decimal = Decimal("0.000000"),
    is_active: bool = True,
) -> BankAccount:
    repo = AccountRepository(db_session)
    account = await repo.create(
        user_id=user_id,
        account_number=account_number,
        account_type=account_type,
        interest_rate=interest_rate,
    )
    account.balance = balance
    account.is_active = is_active
    await db_session.flush()
    return account


# ── user fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
async def customer_user(db_session: AsyncSession) -> User:
    user = await _make_user(
        db_session,
        email="customer@example.com",
        username="customer",
        role=Role.CUSTOMER,
    )
    user.role = Role.CUSTOMER
    await db_session.flush()
    return user


@pytest.fixture
async def teller_user(db_session: AsyncSession) -> User:
    user = await _make_user(
        db_session,
        email="teller@example.com",
        username="teller",
        role=Role.BANK_TELLER,
    )
    user.role = Role.BANK_TELLER
    await db_session.flush()
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = await _make_user(
        db_session,
        email="admin@example.com",
        username="admin",
        role=Role.ADMIN,
    )
    user.role = Role.ADMIN
    await db_session.flush()
    return user


# ── account fixtures ────────────────────────────────────────────────────────


@pytest.fixture
async def checking_account(db_session: AsyncSession, customer_user: User) -> BankAccount:
    return await _make_account(
        db_session,
        user_id=customer_user.id,
        account_number="ACC000000000001",
        account_type="checking",
        balance=Decimal("1000.00"),
    )


@pytest.fixture
async def second_checking_account(db_session: AsyncSession, teller_user: User) -> BankAccount:
    """Owned by the teller user — different owner than checking_account."""
    return await _make_account(
        db_session,
        user_id=teller_user.id,
        account_number="ACC000000000002",
        account_type="checking",
        balance=Decimal("500.00"),
    )


@pytest.fixture
async def savings_account(db_session: AsyncSession, customer_user: User) -> BankAccount:
    return await _make_account(
        db_session,
        user_id=customer_user.id,
        account_number="ACC000000000003",
        account_type="savings",
        balance=Decimal("5000.00"),
        interest_rate=Decimal("0.05"),
    )


@pytest.fixture
async def inactive_account(db_session: AsyncSession, customer_user: User) -> BankAccount:
    return await _make_account(
        db_session,
        user_id=customer_user.id,
        account_number="ACC000000000004",
        account_type="checking",
        balance=Decimal("200.00"),
        is_active=False,
    )
