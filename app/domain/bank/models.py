"""
Banking domain ORM models.

Schema overview
───────────────
bank_accounts  ←──── transactions   (one-to-many, via account_id)
bank_accounts  ←──── transfers      (two FKs: from_account_id, to_account_id)

Atomicity contract
──────────────────
A transfer is represented by:
  1. A row in `transfers`                  (the envelope)
  2. A DEBIT  row in `transactions`        (source ledger entry)
  3. A CREDIT row in `transactions`        (destination ledger entry)

All three are written inside the same SQLAlchemy session/transaction.
The `reference_code` UUID ties the two ledger rows together.
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AccountType:
    CHECKING = "checking"
    SAVINGS = "savings"


class TransactionType:
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class TransferStatus:
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BankAccount(Base):
    """
    Represents a customer's bank account.

    Columns
    ───────
    balance       – stored as NUMERIC(18,2); always >= 0 after a valid transfer.
    interest_rate – annual rate as a decimal (e.g. 0.05 = 5 %).
                    Only meaningful for savings accounts.
    """

    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    account_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    interest_rate: Mapped[Decimal] = mapped_column(
        Numeric(7, 6), default=Decimal("0.000000"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="bank_accounts", foreign_keys=[user_id]
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="account",
        foreign_keys="Transaction.account_id",
    )
    outgoing_transfers: Mapped[list["Transfer"]] = relationship(
        "Transfer",
        back_populates="from_account",
        foreign_keys="Transfer.from_account_id",
    )
    incoming_transfers: Mapped[list["Transfer"]] = relationship(
        "Transfer",
        back_populates="to_account",
        foreign_keys="Transfer.to_account_id",
    )


class Transaction(Base):
    """
    Immutable ledger entry for a single account.

    Every transfer produces exactly two Transaction rows (DEBIT + CREDIT)
    sharing the same `reference_code`.  Interest payments produce one
    CREDIT row with no `reference_code`.

    `balance_after` is a snapshot of the account balance immediately after
    this entry, useful for statement rendering without costly aggregations.
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    reference_code: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    account: Mapped["BankAccount"] = relationship(
        "BankAccount",
        back_populates="transactions",
        foreign_keys=[account_id],
    )


class Transfer(Base):
    """
    High-level record of a completed (or failed) transfer.

    The `reference_code` UUID is the canonical identifier shared with the
    two Transaction ledger rows and returned to the caller.
    """

    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reference_code: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    from_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id"), nullable=False
    )
    to_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    from_account: Mapped["BankAccount"] = relationship(
        "BankAccount",
        back_populates="outgoing_transfers",
        foreign_keys=[from_account_id],
    )
    to_account: Mapped["BankAccount"] = relationship(
        "BankAccount",
        back_populates="incoming_transfers",
        foreign_keys=[to_account_id],
    )
