import random
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.bank.exceptions import (
    AccountInactiveError,
    AccountNotFoundError,
    InsufficientFundsError,
    InvalidAmountError,
    SameAccountTransferError,
)
from app.domain.bank.repository import AccountRepository
from app.domain.bank.schemas import (
    AccountCreateRequest,
    AccountResponse,
    TransferRequest,
    TransferResult,
)
from app.domain.bank.transfer_service import TransferService

router = APIRouter(prefix="/bank", tags=["bank"])


def _generate_account_number() -> str:
    return "ACC" + "".join(random.choices(string.digits, k=12))


@router.post(
    "/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_account(
    request: AccountCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> AccountResponse:
    # get_db provides a session with begin() — COMMIT happens automatically
    # on clean exit; ROLLBACK on any unhandled exception.
    repo = AccountRepository(db)
    account = await repo.create(
        user_id=request.user_id,
        account_number=_generate_account_number(),
        account_type=request.account_type,
        interest_rate=request.interest_rate,
        currency=request.currency,
    )
    return AccountResponse.model_validate(account)


@router.post(
    "/transfers",
    response_model=TransferResult,
    status_code=status.HTTP_200_OK,
)
async def transfer(
    request: TransferRequest,
    db: AsyncSession = Depends(get_db),
) -> TransferResult:
    """Execute a transfer within an atomic DB transaction.

    The session from get_db is already wrapped in begin():
    - Debit + credit + ledger entries all flush inside the same transaction.
    - If TransferService raises a domain exception, we convert it to an
      HTTPException *before* the context manager exits — SQLAlchemy then
      rolls back the transaction automatically.
    - If no exception is raised, begin().__aexit__ commits automatically.
    """
    service = TransferService(db)
    try:
        return await service.transfer(request)
    except (AccountNotFoundError, AccountInactiveError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InsufficientFundsError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    except (InvalidAmountError, SameAccountTransferError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
