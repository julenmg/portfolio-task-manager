from decimal import Decimal


class BankDomainError(Exception):
    """Base exception for all banking domain errors."""


class AccountNotFoundError(BankDomainError):
    def __init__(self, account_id: int) -> None:
        super().__init__(f"Account {account_id} not found")
        self.account_id = account_id


class InsufficientFundsError(BankDomainError):
    def __init__(self, account_id: int, balance: Decimal, amount: Decimal) -> None:
        super().__init__(
            f"Insufficient funds on account {account_id}: "
            f"balance={balance}, requested={amount}"
        )
        self.account_id = account_id
        self.balance = balance
        self.amount = amount


class AccountInactiveError(BankDomainError):
    def __init__(self, account_id: int) -> None:
        super().__init__(f"Account {account_id} is inactive")
        self.account_id = account_id


class SameAccountTransferError(BankDomainError):
    def __init__(self) -> None:
        super().__init__("Cannot transfer to the same account")


class InvalidAmountError(BankDomainError):
    def __init__(self, amount: Decimal) -> None:
        super().__init__(f"Amount must be positive, got {amount}")
        self.amount = amount
