"""Create bank tables: bank_accounts, transactions, transfers.

Revision ID: 0001
Revises:
Create Date: 2026-03-02

Design notes
────────────
All three tables are created inside a single database transaction
(BEGIN … COMMIT).  If any DDL statement fails, the whole migration
is rolled back automatically by ``context.begin_transaction()``.

Atomicity constraint
────────────────────
The CHECK constraint ``ck_bank_accounts_non_negative_balance`` on
``bank_accounts.balance`` is the database-level safety net: it makes
it physically impossible for a balance to go below zero regardless of
which application layer (service, direct SQL, migration script) writes
to the table.

The application layer (TransferService) also validates this before
executing DML, but the DB constraint is the authoritative guard.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# Alembic metadata
revision: str = "0001"
down_revision: str | None = "0000"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


# ---------------------------------------------------------------------------
# Upgrade — forward migration (runs inside BEGIN … COMMIT)
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # ── 1. bank_accounts ────────────────────────────────────────────────────
    #
    # Central entity.  ``balance`` has a CHECK constraint so the DB engine
    # rejects any UPDATE/INSERT that would set it below zero, even when
    # bypassing the application layer.
    #
    op.create_table(
        "bank_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("account_number", sa.String(20), nullable=False),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column(
            "balance",
            sa.Numeric(18, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "interest_rate",
            sa.Numeric(7, 6),
            nullable=False,
            server_default="0.000000",
        ),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # ── Safety net: balance MUST never be negative. ──────────────────
        sa.CheckConstraint(
            "balance >= 0",
            name="ck_bank_accounts_non_negative_balance",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_number", name="uq_bank_accounts_account_number"),
    )
    op.create_index("ix_bank_accounts_id", "bank_accounts", ["id"])
    op.create_index("ix_bank_accounts_user_id", "bank_accounts", ["user_id"])
    op.create_index(
        "ix_bank_accounts_account_number", "bank_accounts", ["account_number"]
    )

    # ── 2. transactions (immutable ledger) ──────────────────────────────────
    #
    # Each row records a single DEBIT or CREDIT on one account.
    # A pair of rows linked by the same ``reference_code`` UUID represents
    # the two legs of one transfer.
    #
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # ``amount`` is always positive; the direction is captured by
        # ``transaction_type`` ("DEBIT" | "CREDIT").
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("transaction_type", sa.String(10), nullable=False),
        # UUID that ties the two legs of a transfer together.
        sa.Column("reference_code", sa.String(36), nullable=True),
        sa.Column("description", sa.String(255), nullable=True),
        # Snapshot of account balance immediately after this entry.
        sa.Column("balance_after", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("amount > 0", name="ck_transactions_positive_amount"),
        sa.CheckConstraint(
            "transaction_type IN ('DEBIT', 'CREDIT')",
            name="ck_transactions_valid_type",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_id", "transactions", ["id"])
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index(
        "ix_transactions_reference_code", "transactions", ["reference_code"]
    )

    # ── 3. transfers (transfer envelope) ────────────────────────────────────
    #
    # High-level record linking the two account legs of a transfer.
    # The ``reference_code`` is returned to the caller and shared with both
    # Transaction ledger rows.
    #
    op.create_table(
        "transfers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reference_code", sa.String(36), nullable=False),
        sa.Column(
            "from_account_id",
            sa.Integer(),
            sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "to_account_id",
            sa.Integer(),
            sa.ForeignKey("bank_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("amount > 0", name="ck_transfers_positive_amount"),
        sa.CheckConstraint(
            "from_account_id <> to_account_id",
            name="ck_transfers_different_accounts",
        ),
        sa.CheckConstraint(
            "status IN ('COMPLETED', 'FAILED')",
            name="ck_transfers_valid_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference_code", name="uq_transfers_reference_code"),
    )
    op.create_index("ix_transfers_id", "transfers", ["id"])
    op.create_index(
        "ix_transfers_reference_code", "transfers", ["reference_code"]
    )


# ---------------------------------------------------------------------------
# Downgrade — reverse migration (also runs inside BEGIN … COMMIT)
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # Drop in reverse dependency order.
    op.drop_table("transfers")
    op.drop_table("transactions")
    op.drop_table("bank_accounts")
