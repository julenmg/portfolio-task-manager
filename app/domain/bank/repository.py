from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.bank.models import BankAccount, Transaction, Transfer


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, account_id: int) -> BankAccount | None:
        result = await self._session.execute(
            select(BankAccount).where(BankAccount.id == account_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, account_id: int) -> BankAccount | None:
        """Acquire a pessimistic write lock on the row (SELECT … FOR UPDATE).

        On SQLite (used in tests) the clause is silently ignored; the
        serialised write model of SQLite already prevents lost updates.
        """
        result = await self._session.execute(
            select(BankAccount)
            .where(BankAccount.id == account_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_many_for_update(self, *account_ids: int) -> list[BankAccount]:
        """Lock multiple accounts in ascending ID order to prevent deadlocks.

        Always acquiring locks in a consistent order (lowest ID first) ensures
        that two concurrent transfers between the same pair of accounts can
        never form a circular wait.
        """
        ordered_ids = sorted(set(account_ids))
        result = await self._session.execute(
            select(BankAccount)
            .where(BankAccount.id.in_(ordered_ids))
            .order_by(BankAccount.id)
            .with_for_update()
        )
        return list(result.scalars().all())

    async def create(
        self,
        *,
        user_id: int,
        account_number: str,
        account_type: str,
        interest_rate: Decimal = Decimal("0.000000"),
        currency: str = "EUR",
    ) -> BankAccount:
        account = BankAccount(
            user_id=user_id,
            account_number=account_number,
            account_type=account_type,
            interest_rate=interest_rate,
            currency=currency,
        )
        self._session.add(account)
        await self._session.flush()
        await self._session.refresh(account)
        return account

    async def update_balance(self, account: BankAccount, new_balance: Decimal) -> None:
        account.balance = new_balance
        account.updated_at = datetime.now(timezone.utc)
        self._session.add(account)


class TransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        account_id: int,
        amount: Decimal,
        transaction_type: str,
        balance_after: Decimal,
        reference_code: str | None = None,
        description: str | None = None,
    ) -> Transaction:
        txn = Transaction(
            account_id=account_id,
            amount=amount,
            transaction_type=transaction_type,
            reference_code=reference_code,
            description=description,
            balance_after=balance_after,
        )
        self._session.add(txn)
        await self._session.flush()
        return txn

    async def get_by_reference(self, reference_code: str) -> list[Transaction]:
        result = await self._session.execute(
            select(Transaction).where(Transaction.reference_code == reference_code)
        )
        return list(result.scalars().all())


class TransferRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        reference_code: str,
        from_account_id: int,
        to_account_id: int,
        amount: Decimal,
        description: str | None,
        status: str,
        completed_at: datetime | None = None,
    ) -> Transfer:
        transfer = Transfer(
            reference_code=reference_code,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            description=description,
            status=status,
            completed_at=completed_at,
        )
        self._session.add(transfer)
        await self._session.flush()
        return transfer

    async def get_by_reference(self, reference_code: str) -> Transfer | None:
        result = await self._session.execute(
            select(Transfer).where(Transfer.reference_code == reference_code)
        )
        return result.scalar_one_or_none()
