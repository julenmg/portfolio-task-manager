import random
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.auth.dependencies import get_current_user, require_roles
from app.domain.bank.exceptions import (
    AccountInactiveError,
    AccountNotFoundError,
    InsufficientFundsError,
    InvalidAmountError,
    SameAccountTransferError,
)
from app.domain.bank.models import BankAccount
from app.domain.bank.repository import AccountRepository, TransactionRepository
from app.domain.bank.schemas import (
    AccountCreateRequest,
    AccountResponse,
    TransactionResponse,
    TransferRequest,
    TransferResult,
)
from app.domain.bank.transfer_service import TransferService
from app.models.user import Role, User

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
    current_user: User = Depends(require_roles(Role.BANK_TELLER, Role.ADMIN)),
) -> AccountResponse:
    """Create a bank account.  Requires BankTeller or Admin role."""
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
    current_user: User = Depends(get_current_user),
) -> TransferResult:
    """Execute a transfer within an atomic DB transaction.

    - **Customer**: can only transfer from an account they own.
    - **BankTeller / Admin**: can transfer between any accounts.

    The session from get_db is already wrapped in begin():
    - Debit + credit + ledger entries all flush inside the same transaction.
    - On any domain exception we raise an HTTPException before the context
      manager exits — SQLAlchemy rolls back automatically.
    - On clean exit, begin().__aexit__ commits automatically.
    """
    # Ownership check for customers
    if current_user.role == Role.CUSTOMER:
        account_repo = AccountRepository(db)
        from_account = await account_repo.get_by_id(request.from_account_id)
        if from_account is None or from_account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only transfer from your own accounts",
            )

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


@router.get(
    "/accounts",
    response_model=list[AccountResponse],
)
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AccountResponse]:
    """List bank accounts.

    - **Customer**: sees only their own accounts.
    - **BankTeller / Admin**: sees all accounts.
    """
    if current_user.role == Role.CUSTOMER:
        result = await db.execute(
            select(BankAccount).where(BankAccount.user_id == current_user.id)
        )
    else:
        result = await db.execute(select(BankAccount))

    accounts = list(result.scalars().all())
    return [AccountResponse.model_validate(a) for a in accounts]


@router.get(
    "/accounts/{account_id}",
    response_model=AccountResponse,
)
async def get_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountResponse:
    """Get a single bank account by ID.

    - **Customer**: can only view their own accounts.
    - **BankTeller / Admin**: can view any account.
    """
    repo = AccountRepository(db)
    account = await repo.get_by_id(account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if current_user.role == Role.CUSTOMER and account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own accounts",
        )
    return AccountResponse.model_validate(account)


@router.get(
    "/accounts/{account_id}/transactions",
    response_model=list[TransactionResponse],
)
async def get_transactions(
    account_id: int,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TransactionResponse]:
    """Return ledger entries for an account, newest first.

    - **Customer**: can only view transactions for their own accounts.
    - **BankTeller / Admin**: can view transactions for any account.
    """
    account_repo = AccountRepository(db)
    account = await account_repo.get_by_id(account_id)

    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    if current_user.role == Role.CUSTOMER and account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view transactions for your own accounts",
        )

    txn_repo = TransactionRepository(db)
    transactions = await txn_repo.get_by_account(account_id, limit=limit, offset=offset)
    return [TransactionResponse.model_validate(t) for t in transactions]
