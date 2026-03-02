"""
Tests for TransferService — atomic money transfers.

Coverage checklist
──────────────────
 [x] Successful transfer: balances updated correctly
 [x] Successful transfer: DEBIT + CREDIT ledger entries created
 [x] Successful transfer: Transfer record saved with COMPLETED status
 [x] Successful transfer: reference_code is shared across both ledger entries
 [x] Insufficient funds: raises InsufficientFundsError, balances unchanged
 [x] Same account: raises SameAccountTransferError
 [x] Source account not found: raises AccountNotFoundError
 [x] Destination account not found: raises AccountNotFoundError
 [x] Inactive source account: raises AccountInactiveError
 [x] Inactive destination account: raises AccountInactiveError
 [x] Zero amount: raises InvalidAmountError
 [x] Negative amount: raises InvalidAmountError
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bank.exceptions import (
    AccountInactiveError,
    AccountNotFoundError,
    InsufficientFundsError,
    InvalidAmountError,
    SameAccountTransferError,
)
from app.domain.bank.models import BankAccount, TransactionType, TransferStatus
from app.domain.bank.repository import TransactionRepository, TransferRepository
from app.domain.bank.schemas import TransferRequest
from app.domain.bank.transfer_service import TransferService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _req(
    from_id: int,
    to_id: int,
    amount: str,
    description: str | None = None,
) -> TransferRequest:
    return TransferRequest(
        from_account_id=from_id,
        to_account_id=to_id,
        amount=Decimal(amount),
        description=description,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_transfer_updates_balances(
    db_session: AsyncSession,
    checking_account: BankAccount,
    second_checking_account: BankAccount,
) -> None:
    service = TransferService(db_session)
    result = await service.transfer(
        _req(checking_account.id, second_checking_account.id, "200.00")
    )

    assert result.from_balance_after == Decimal("800.00")
    assert result.to_balance_after == Decimal("700.00")
    assert checking_account.balance == Decimal("800.00")
    assert second_checking_account.balance == Decimal("700.00")


async def test_transfer_creates_debit_and_credit_entries(
    db_session: AsyncSession,
    checking_account: BankAccount,
    second_checking_account: BankAccount,
) -> None:
    service = TransferService(db_session)
    result = await service.transfer(
        _req(checking_account.id, second_checking_account.id, "150.00")
    )

    txn_repo = TransactionRepository(db_session)
    entries = await txn_repo.get_by_reference(result.reference_code)

    assert len(entries) == 2
    types = {e.transaction_type for e in entries}
    assert types == {TransactionType.DEBIT, TransactionType.CREDIT}


async def test_transfer_ledger_entries_share_reference_code(
    db_session: AsyncSession,
    checking_account: BankAccount,
    second_checking_account: BankAccount,
) -> None:
    service = TransferService(db_session)
    result = await service.transfer(
        _req(checking_account.id, second_checking_account.id, "50.00")
    )

    txn_repo = TransactionRepository(db_session)
    entries = await txn_repo.get_by_reference(result.reference_code)

    assert all(e.reference_code == result.reference_code for e in entries)


async def test_transfer_saves_transfer_record_as_completed(
    db_session: AsyncSession,
    checking_account: BankAccount,
    second_checking_account: BankAccount,
) -> None:
    service = TransferService(db_session)
    result = await service.transfer(
        _req(
            checking_account.id,
            second_checking_account.id,
            "300.00",
            description="Rent payment",
        )
    )

    transfer_repo = TransferRepository(db_session)
    transfer = await transfer_repo.get_by_reference(result.reference_code)

    assert transfer is not None
    assert transfer.status == TransferStatus.COMPLETED
    assert transfer.amount == Decimal("300.00")
    assert transfer.description == "Rent payment"
    assert transfer.completed_at is not None


async def test_transfer_result_contains_reference_code(
    db_session: AsyncSession,
    checking_account: BankAccount,
    second_checking_account: BankAccount,
) -> None:
    service = TransferService(db_session)
    result = await service.transfer(
        _req(checking_account.id, second_checking_account.id, "10.00")
    )

    assert result.reference_code
    assert len(result.reference_code) == 36  # UUID format


# ---------------------------------------------------------------------------
# Business-rule violations
# ---------------------------------------------------------------------------


async def test_transfer_insufficient_funds_raises(
    db_session: AsyncSession,
    checking_account: BankAccount,
    second_checking_account: BankAccount,
) -> None:
    service = TransferService(db_session)
    original_from = checking_account.balance
    original_to = second_checking_account.balance

    with pytest.raises(InsufficientFundsError):
        await service.transfer(
            _req(checking_account.id, second_checking_account.id, "9999.00")
        )

    # Balances must be untouched (no commit happened)
    assert checking_account.balance == original_from
    assert second_checking_account.balance == original_to


async def test_transfer_same_account_raises(
    db_session: AsyncSession,
    checking_account: BankAccount,
) -> None:
    service = TransferService(db_session)
    with pytest.raises(SameAccountTransferError):
        await service.transfer(
            _req(checking_account.id, checking_account.id, "100.00")
        )


async def test_transfer_source_not_found_raises(
    db_session: AsyncSession,
    checking_account: BankAccount,
) -> None:
    service = TransferService(db_session)
    with pytest.raises(AccountNotFoundError) as exc_info:
        await service.transfer(_req(99999, checking_account.id, "50.00"))
    assert exc_info.value.account_id == 99999


async def test_transfer_destination_not_found_raises(
    db_session: AsyncSession,
    checking_account: BankAccount,
) -> None:
    service = TransferService(db_session)
    with pytest.raises(AccountNotFoundError) as exc_info:
        await service.transfer(_req(checking_account.id, 99999, "50.00"))
    assert exc_info.value.account_id == 99999


async def test_transfer_inactive_source_raises(
    db_session: AsyncSession,
    inactive_account: BankAccount,
    checking_account: BankAccount,
) -> None:
    service = TransferService(db_session)
    with pytest.raises(AccountInactiveError):
        await service.transfer(
            _req(inactive_account.id, checking_account.id, "50.00")
        )


async def test_transfer_inactive_destination_raises(
    db_session: AsyncSession,
    checking_account: BankAccount,
    inactive_account: BankAccount,
) -> None:
    service = TransferService(db_session)
    with pytest.raises(AccountInactiveError):
        await service.transfer(
            _req(checking_account.id, inactive_account.id, "50.00")
        )


async def test_transfer_zero_amount_raises(
    db_session: AsyncSession,
    checking_account: BankAccount,
    second_checking_account: BankAccount,
) -> None:
    # Use model_construct to bypass Pydantic's gt=0 guard so we reach the
    # service-layer check, which is the behaviour under test here.
    service = TransferService(db_session)
    bad_req = TransferRequest.model_construct(
        from_account_id=checking_account.id,
        to_account_id=second_checking_account.id,
        amount=Decimal("0.00"),
    )
    with pytest.raises(InvalidAmountError):
        await service.transfer(bad_req)


async def test_transfer_negative_amount_raises(
    db_session: AsyncSession,
    checking_account: BankAccount,
    second_checking_account: BankAccount,
) -> None:
    service = TransferService(db_session)
    bad_req = TransferRequest.model_construct(
        from_account_id=checking_account.id,
        to_account_id=second_checking_account.id,
        amount=Decimal("-50.00"),
    )
    with pytest.raises(InvalidAmountError):
        await service.transfer(bad_req)
