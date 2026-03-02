from decimal import Decimal

from pydantic import BaseModel, Field


class AccountCreateRequest(BaseModel):
    user_id: int
    account_type: str = Field(..., pattern="^(checking|savings)$")
    interest_rate: Decimal = Field(default=Decimal("0.00"), ge=0, le=1)
    currency: str = Field(default="EUR", min_length=3, max_length=3)


class AccountResponse(BaseModel):
    id: int
    user_id: int
    account_number: str
    account_type: str
    balance: Decimal
    interest_rate: Decimal
    currency: str
    is_active: bool

    model_config = {"from_attributes": True}


class TransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    description: str | None = Field(default=None, max_length=255)


class TransferResult(BaseModel):
    reference_code: str
    from_account_id: int
    to_account_id: int
    amount: Decimal
    from_balance_after: Decimal
    to_balance_after: Decimal
