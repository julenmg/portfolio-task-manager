from decimal import Decimal
from enum import Enum

class CompoundingPeriod(Enum):
    MONTHLY = "monthly"
    ANNUALLY = "annually"

class InterestCalculator:
    @staticmethod
    def calculate_compound_interest(
        principal: Decimal,
        annual_rate: Decimal,
        days: int,
        compounding: CompoundingPeriod = CompoundingPeriod.MONTHLY,
    ) -> Decimal:
        """Return interest earned (not the accrued total).

        Args:
            principal:   Starting balance.
            annual_rate: Annual interest rate (as a decimal).
            days:        Number of days the interest is applied.
            compounding: Compounding period (default is monthly).
        """
        if compounding == CompoundingPeriod.MONTHLY:
            n = 12
        elif compounding == CompoundingPeriod.ANNUALLY:
            n = 1
        else:
            raise ValueError("Invalid compounding period")

        t = days / 365
        i = principal * (1 + annual_rate / n) ** (n * t) - principal
        return i
