"""Banking domain exceptions.

Public messages are intentionally generic to avoid leaking account IDs,
balances, or other financial details to API consumers.  Internal attributes
(account_id, balance, amount) are available for server-side logging only.
"""

from decimal import Decimal


class BankDomainError(Exception):
    """Base exception for all banking domain errors."""


class AccountNotFoundError(BankDomainError):
    def __init__(self, account_id: int) -> None:
        super().__init__("Account not found")
        self.account_id = account_id


class InsufficientFundsError(BankDomainError):
    def __init__(self, account_id: int, balance: Decimal, amount: Decimal) -> None:
        super().__init__("Insufficient funds")
        self.account_id = account_id
        self.balance = balance
        self.amount = amount


class AccountInactiveError(BankDomainError):
    # Deliberately uses the same message as AccountNotFoundError to prevent
    # enumeration of active vs. inactive account states.
    def __init__(self, account_id: int) -> None:
        super().__init__("Account not found")
        self.account_id = account_id


class SameAccountTransferError(BankDomainError):
    def __init__(self) -> None:
        super().__init__("Cannot transfer to the same account")


class InvalidAmountError(BankDomainError):
    def __init__(self, amount: Decimal) -> None:
        super().__init__("Transfer amount must be positive")
        self.amount = amount
