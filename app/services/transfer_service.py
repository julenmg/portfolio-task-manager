from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transfer import TransferRequest
from app.services.user_service import UserService
from app.schemas.user import UserRegisterRequest

class TransferService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def transfer(self, sender_id: int, receiver_id: int, request: TransferRequest) -> None:
        if sender_id == receiver_id:
            raise ValueError('El ID de la cuenta de origen y destino no pueden ser el mismo')

        sender = await self.db.execute(select(Account).where(Account.id == sender_id))
        receiver = await self.db.execute(select(Account).where(Account.id == receiver_id))
        sender_account = sender.scalar_one_or_none()
        receiver_account = receiver.scalar_one_or_none()

        if not sender_account or not receiver_account:
            raise ValueError('Cuentas no encontradas')

        if sender_account.balance < request.amount:
            raise ValueError('Saldo insuficiente')

        sender_account.balance -= request.amount
        receiver_account.balance += request.amount

        transaction = Transaction(
            amount=request.amount,
            currency=request.currency,
            account_id=sender_id
        )

        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
