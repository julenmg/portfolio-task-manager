from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transfer import TransferRequest
from app.services.transfer_service import TransferService
from app.services.user_service import UserService
from app.schemas.user import UserRegisterRequest
import pytest

@pytest.mark.asyncio
async def test_transfer_success(db_session: AsyncSession):
    user_service = UserService(db_session)
    user = await user_service.register(UserRegisterRequest(email="test@example.com", username="test", password="password"))
    account = await db_session.execute(select(Account).where(Account.user_id == user.id))
    account = account.scalar_one_or_none()

    transfer_service = TransferService(db_session)
    await transfer_service.transfer(account.id, account.id, TransferRequest(amount=100, currency="USD"))

    updated_account = await db_session.execute(select(Account).where(Account.id == account.id))
    updated_account = updated_account.scalar_one_or_none()

    assert updated_account.balance == 0

@pytest.mark.asyncio
async def test_transfer_insufficient_balance(db_session: AsyncSession):
    user_service = UserService(db_session)
    user = await user_service.register(UserRegisterRequest(email="test@example.com", username="test", password="password"))
    account = await db_session.execute(select(Account).where(Account.user_id == user.id))
    account = account.scalar_one_or_none()

    transfer_service = TransferService(db_session)
    with pytest.raises(ValueError) as exc_info:
        await transfer_service.transfer(account.id, account.id, TransferRequest(amount=200, currency="USD"))

    assert str(exc_info.value) == 'Saldo insuficiente'
