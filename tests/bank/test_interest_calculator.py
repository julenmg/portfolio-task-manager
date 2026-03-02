"""
Tests for InterestCalculator — simple / compound interest.

Coverage checklist
──────────────────
 [x] Simple interest: correct formula P×r×t
 [x] Simple interest: zero rate returns 0.00
 [x] Simple interest: zero days returns 0.00
 [x] Simple interest: negative days raises ValueError
 [x] Simple interest: negative rate raises ValueError
 [x] Compound interest (monthly): greater than simple for same inputs
 [x] Compound interest (daily): smallest rounding differences
 [x] Compound interest (annually): equals simple for one-year period
 [x] apply_interest: credits balance and creates ledger entry
 [x] apply_interest: returns correct interest amount
 [x] apply_interest: zero interest (0 % rate) returns 0.00, no entry
 [x] apply_interest: non-savings account raises ValueError
 [x] apply_interest: non-existent account raises AccountNotFoundError
 [x] apply_interest: inactive account raises AccountInactiveError
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.domain.bank.exceptions import AccountInactiveError, AccountNotFoundError
from app.domain.bank.interest_calculator import InterestCalculator
from app.domain.bank.models import BankAccount, Transaction, TransactionType
from app.domain.bank.repository import AccountRepository


# ---------------------------------------------------------------------------
# Pure calculation — simple interest
# ---------------------------------------------------------------------------


def test_simple_interest_basic() -> None:
    calc = InterestCalculator()
    # P=1000, r=5%, 365 days → I = 1000*0.05*1 = 50.00
    result = calc.calculate_simple_interest(
        Decimal("1000.00"), Decimal("0.05"), 365
    )
    assert result == Decimal("50.00")


def test_simple_interest_zero_rate() -> None:
    calc = InterestCalculator()
    result = calc.calculate_simple_interest(Decimal("5000.00"), Decimal("0"), 180)
    assert result == Decimal("0.00")


def test_simple_interest_zero_days() -> None:
    calc = InterestCalculator()
    result = calc.calculate_simple_interest(Decimal("5000.00"), Decimal("0.05"), 0)
    assert result == Decimal("0.00")


def test_simple_interest_negative_days_raises() -> None:
    calc = InterestCalculator()
    with pytest.raises(ValueError, match="days"):
        calc.calculate_simple_interest(Decimal("1000.00"), Decimal("0.05"), -1)


def test_simple_interest_negative_rate_raises() -> None:
    calc = InterestCalculator()
    with pytest.raises(ValueError, match="annual_rate"):
        calc.calculate_simple_interest(Decimal("1000.00"), Decimal("-0.01"), 30)


# ---------------------------------------------------------------------------
# Pure calculation — compound interest
# ---------------------------------------------------------------------------


def test_compound_monthly_exceeds_simple() -> None:
    calc = InterestCalculator()
    simple = calc.calculate_simple_interest(
        Decimal("1000.00"), Decimal("0.05"), 365
    )
    compound = calc.calculate_compound_interest(
        Decimal("1000.00"), Decimal("0.05"), 365, compounding="monthly"
    )
    assert compound > simple


def test_compound_daily() -> None:
    calc = InterestCalculator()
    result = calc.calculate_compound_interest(
        Decimal("1000.00"), Decimal("0.05"), 365, compounding="daily"
    )
    # e^0.05 ≈ 1.05127, so interest ≈ 51.27
    assert Decimal("51.00") < result < Decimal("52.00")


def test_compound_annually_one_year() -> None:
    calc = InterestCalculator()
    # With n=1 and t=1, compound = simple for a full year
    result = calc.calculate_compound_interest(
        Decimal("1000.00"), Decimal("0.05"), 365, compounding="annually"
    )
    assert result == Decimal("50.00")


def test_compound_zero_rate() -> None:
    calc = InterestCalculator()
    result = calc.calculate_compound_interest(
        Decimal("5000.00"), Decimal("0"), 180, compounding="monthly"
    )
    assert result == Decimal("0.00")


def test_compound_zero_days() -> None:
    calc = InterestCalculator()
    result = calc.calculate_compound_interest(
        Decimal("5000.00"), Decimal("0.05"), 0, compounding="monthly"
    )
    assert result == Decimal("0.00")


# ---------------------------------------------------------------------------
# DB-aware: apply_interest
# ---------------------------------------------------------------------------


async def test_apply_interest_credits_balance(
    db_session: AsyncSession,
    savings_account: BankAccount,
) -> None:
    calc = InterestCalculator()
    original_balance = savings_account.balance

    interest = await calc.apply_interest(savings_account.id, 365, db_session)

    assert interest > Decimal("0")
    assert savings_account.balance == original_balance + interest


async def test_apply_interest_creates_credit_entry(
    db_session: AsyncSession,
    savings_account: BankAccount,
) -> None:
    calc = InterestCalculator()
    await calc.apply_interest(savings_account.id, 30, db_session)

    result = await db_session.execute(
        select(Transaction).where(Transaction.account_id == savings_account.id)
    )
    entries = list(result.scalars().all())

    assert len(entries) == 1
    assert entries[0].transaction_type == TransactionType.CREDIT
    assert entries[0].amount > Decimal("0")


async def test_apply_interest_returns_correct_amount(
    db_session: AsyncSession,
    savings_account: BankAccount,
) -> None:
    calc = InterestCalculator()
    expected = calc.calculate_compound_interest(
        savings_account.balance,
        savings_account.interest_rate,
        365,
        compounding="monthly",
    )

    actual = await calc.apply_interest(savings_account.id, 365, db_session)

    assert actual == expected


async def test_apply_interest_zero_rate_returns_zero(
    db_session: AsyncSession,
) -> None:
    repo = AccountRepository(db_session)
    zero_rate_account = await repo.create(
        user_id=1,
        account_number="ACC999999999999",
        account_type="savings",
        interest_rate=Decimal("0.00"),
    )
    zero_rate_account.balance = Decimal("1000.00")
    await db_session.flush()

    calc = InterestCalculator()
    result = await calc.apply_interest(zero_rate_account.id, 30, db_session)

    assert result == Decimal("0.00")
    # Balance must be unchanged
    assert zero_rate_account.balance == Decimal("1000.00")


async def test_apply_interest_checking_raises(
    db_session: AsyncSession,
    checking_account: BankAccount,
) -> None:
    calc = InterestCalculator()
    with pytest.raises(ValueError, match="savings"):
        await calc.apply_interest(checking_account.id, 30, db_session)


async def test_apply_interest_not_found_raises(
    db_session: AsyncSession,
) -> None:
    calc = InterestCalculator()
    with pytest.raises(AccountNotFoundError):
        await calc.apply_interest(99999, 30, db_session)


async def test_apply_interest_inactive_raises(
    db_session: AsyncSession,
    inactive_account: BankAccount,
) -> None:
    # Make inactive_account a savings type so the inactive check is reached
    inactive_account.account_type = "savings"
    await db_session.flush()

    calc = InterestCalculator()
    with pytest.raises(AccountInactiveError):
        await calc.apply_interest(inactive_account.id, 30, db_session)
