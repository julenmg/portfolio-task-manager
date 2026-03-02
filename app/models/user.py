import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Role(str, enum.Enum):
    """User roles for RBAC.

    - CUSTOMER   : owns accounts, sees own history, transfers from own accounts.
    - BANK_TELLER: views any account/history, executes transfers for any account.
    - ADMIN      : full access + audit log.
    """

    CUSTOMER = "customer"
    BANK_TELLER = "bank_teller"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="userrole"),
        default=Role.CUSTOMER,
        server_default=Role.CUSTOMER.value,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    bank_accounts: Mapped[list["BankAccount"]] = relationship(  # type: ignore[name-defined]
        "BankAccount", back_populates="user", foreign_keys="BankAccount.user_id"
    )
