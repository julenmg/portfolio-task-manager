"""
TransferService — atomic money transfer between two bank accounts.

Atomicity guarantee
───────────────────
All writes (balance updates, ledger entries, transfer record) happen inside
the same SQLAlchemy AsyncSession that the caller provides.  The caller is
responsible for committing (success) or rolling back (failure) that session.
If any step raises an exception the session is left in a dirty-but-uncommitted
state; an outer `async with session.begin()` or an explicit rollback will
discard all partial writes, leaving both accounts untouched.

Deadlock prevention
───────────────────
`AccountRepository.get_many_for_update` always acquires row-level locks in
ascending account-ID order.  This canonical ordering guarantees that two
concurrent transfers between the same pair of accounts will never create a
circular wait (both will always try to lock the lower-ID account first).
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bank.exceptions import (
    AccountInactiveError,
    AccountNotFoundError,
    InsufficientFundsError,
    InvalidAmountError,
    SameAccountTransferError,
)
from app.domain.bank.models import TransactionType, TransferStatus
from app.domain.bank.repository import (
    AccountRepository,
    TransactionRepository,
    TransferRepository,
)
from app.domain.bank.schemas import TransferRequest, TransferResult


class TransferService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._accounts = AccountRepository(session)
        self._transactions = TransactionRepository(session)
        self._transfers = TransferRepository(session)

    async def transfer(self, request: TransferRequest) -> TransferResult:
        """Execute an atomic debit/credit transfer.

        Steps (all within the same DB transaction):
          1. Validate inputs.
          2. Lock both account rows in ID order (FOR UPDATE).
          3. Validate business rules (active, sufficient funds).
          4. Update balances in memory.
          5. Write DEBIT ledger entry.
          6. Write CREDIT ledger entry.
          7. Write Transfer record (COMPLETED).
          8. Return result — the caller commits.

        Any exception rolls back all of the above automatically.
        """
        if request.amount <= Decimal("0"):
            raise InvalidAmountError(request.amount)

        if request.from_account_id == request.to_account_id:
            raise SameAccountTransferError()

        # --- Step 2: lock rows in deterministic order ---
        accounts = await self._accounts.get_many_for_update(
            request.from_account_id, request.to_account_id
        )
        by_id = {a.id: a for a in accounts}

        from_account = by_id.get(request.from_account_id)
        to_account = by_id.get(request.to_account_id)

        if from_account is None:
            raise AccountNotFoundError(request.from_account_id)
        if to_account is None:
            raise AccountNotFoundError(request.to_account_id)

        # --- Step 3: business-rule validation ---
        if not from_account.is_active:
            raise AccountInactiveError(request.from_account_id)
        if not to_account.is_active:
            raise AccountInactiveError(request.to_account_id)
        if from_account.balance < request.amount:
            raise InsufficientFundsError(
                request.from_account_id, from_account.balance, request.amount
            )

        reference_code = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # --- Steps 4-7: atomic writes ---
        new_from_balance = from_account.balance - request.amount
        new_to_balance = to_account.balance + request.amount

        await self._accounts.update_balance(from_account, new_from_balance)
        await self._accounts.update_balance(to_account, new_to_balance)

        await self._transactions.create(
            account_id=from_account.id,
            amount=request.amount,
            transaction_type=TransactionType.DEBIT,
            balance_after=new_from_balance,
            reference_code=reference_code,
            description=request.description,
        )
        await self._transactions.create(
            account_id=to_account.id,
            amount=request.amount,
            transaction_type=TransactionType.CREDIT,
            balance_after=new_to_balance,
            reference_code=reference_code,
            description=request.description,
        )

        await self._transfers.create(
            reference_code=reference_code,
            from_account_id=from_account.id,
            to_account_id=to_account.id,
            amount=request.amount,
            description=request.description,
            status=TransferStatus.COMPLETED,
            completed_at=now,
        )

        return TransferResult(
            reference_code=reference_code,
            from_account_id=from_account.id,
            to_account_id=to_account.id,
            amount=request.amount,
            from_balance_after=new_from_balance,
            to_balance_after=new_to_balance,
        )
