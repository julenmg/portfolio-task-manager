"""
InterestCalculator — simple and compound interest for bank accounts.

Formulae
────────
Simple interest:
    I = P × r × t
    where t = days / 365

Compound interest:
    I = P × (1 + r/n)^(n×t) − P
    where n = compounding periods per year, t = days / 365

All monetary results are rounded to 2 decimal places (ROUND_HALF_UP).
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bank.exceptions import AccountInactiveError, AccountNotFoundError
from app.domain.bank.models import TransactionType
from app.domain.bank.repository import AccountRepository, TransactionRepository


CompoundingPeriod = Literal["daily", "monthly", "annually"]

_PERIODS_PER_YEAR: dict[str, int] = {
    "daily": 365,
    "monthly": 12,
    "annually": 1,
}


class InterestCalculator:
    # ------------------------------------------------------------------ #
    # Pure calculation methods (no DB access, fully testable in isolation) #
    # ------------------------------------------------------------------ #

    @staticmethod
    def calculate_simple_interest(
        principal: Decimal,
        annual_rate: Decimal,
        days: int,
    ) -> Decimal:
        """Return interest earned (not the accrued total).

        Args:
            principal:   Starting balance.
            annual_rate: Annual rate as a decimal (e.g. 0.05 = 5 %).
            days:        Number of days the interest accrues.

        Returns:
            Interest amount rounded to 2 decimal places.

        Raises:
            ValueError: If days or annual_rate is negative.
        """
        if days < 0:
            raise ValueError("days must be >= 0")
        if annual_rate < 0:
            raise ValueError("annual_rate must be >= 0")

        interest = principal * annual_rate * Decimal(days) / Decimal(365)
        return interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def calculate_compound_interest(
        principal: Decimal,
        annual_rate: Decimal,
        days: int,
        compounding: CompoundingPeriod = "monthly",
    ) -> Decimal:
        """Return interest earned (not the accrued total).

        Args:
            principal:   Starting balance.
            annual_rate: Annual rate as a decimal (e.g. 0.05 = 5 %).
            days:        Number of days the interest accrues.
            compounding: How often interest compounds ('daily', 'monthly', 'annually').

        Returns:
            Interest amount rounded to 2 decimal places.

        Raises:
            ValueError: If days or annual_rate is negative.
        """
        if days < 0:
            raise ValueError("days must be >= 0")
        if annual_rate < 0:
            raise ValueError("annual_rate must be >= 0")

        n = Decimal(_PERIODS_PER_YEAR[compounding])
        t = Decimal(days) / Decimal(365)

        accrued = principal * (1 + annual_rate / n) ** (n * t)
        interest = accrued - principal
        return interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # ------------------------------------------------------------------ #
    # DB-aware method                                                       #
    # ------------------------------------------------------------------ #

    async def apply_interest(
        self,
        account_id: int,
        days: int,
        session: AsyncSession,
        compounding: CompoundingPeriod = "monthly",
    ) -> Decimal:
        """Calculate compound interest and credit it to a savings account.

        The caller is responsible for committing the session.

        Args:
            account_id:  Target account.
            days:        Accrual period in days.
            session:     Active AsyncSession (caller manages commit/rollback).
            compounding: Compounding frequency.

        Returns:
            Interest amount credited (Decimal, 2 d.p.).  Returns 0.00 if
            the calculated interest rounds to zero.

        Raises:
            AccountNotFoundError:  Account does not exist.
            AccountInactiveError:  Account exists but is inactive.
            ValueError:            Account type is not 'savings'.
        """
        account_repo = AccountRepository(session)
        transaction_repo = TransactionRepository(session)

        account = await account_repo.get_by_id_for_update(account_id)
        if account is None:
            raise AccountNotFoundError(account_id)
        if not account.is_active:
            raise AccountInactiveError(account_id)
        if account.account_type != "savings":
            raise ValueError(
                f"Interest only applies to savings accounts, got '{account.account_type}'"
            )

        interest = self.calculate_compound_interest(
            principal=account.balance,
            annual_rate=account.interest_rate,
            days=days,
            compounding=compounding,
        )

        if interest <= Decimal("0"):
            return Decimal("0.00")

        new_balance = account.balance + interest
        await account_repo.update_balance(account, new_balance)
        await transaction_repo.create(
            account_id=account_id,
            amount=interest,
            transaction_type=TransactionType.CREDIT,
            balance_after=new_balance,
            description=f"Interest credit ({days}d, {compounding})",
        )

        return interest
