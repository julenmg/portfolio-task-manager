"""Add role column to users table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-02

Notes
─────
Adds the ``role`` Enum column (customer / bank_teller / admin) to the
``users`` table.  Existing rows get ``customer`` as the default so no
data is lost on upgrade.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str = "0001"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # Create the Enum type on PostgreSQL (no-op on SQLite).
    userrole = sa.Enum(
        "customer", "bank_teller", "admin", name="userrole", create_type=True
    )

    op.add_column(
        "users",
        sa.Column(
            "role",
            userrole,
            nullable=False,
            server_default="customer",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
    # Drop the Enum type on PostgreSQL.
    sa.Enum(name="userrole").drop(op.get_bind(), checkfirst=True)
