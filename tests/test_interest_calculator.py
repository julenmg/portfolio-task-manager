import pytest
from decimal import Decimal

from app.services.interest_calculator import CompoundingPeriod, InterestCalculator


def test_compound_monthly():
    """Monthly compounding for 30 days at 5 % annual on 1000 principal.

    I = P · (1 + r/n)^(n·t) − P
    n=12, t=30/365 ≈ 0.08219, n·t ≈ 0.9863
    Expected ≈ 4.11 (not 4.175 — the old expected value was incorrect).
    """
    principal = Decimal("1000")
    annual_rate = Decimal("0.05")
    days = 30

    result = InterestCalculator.calculate_compound_interest(
        principal, annual_rate, days, CompoundingPeriod.MONTHLY
    )

    # Use a relative tolerance of 0.1 % — exact Decimal value is ≈ 4.109...
    assert float(result) == pytest.approx(4.109, rel=1e-2)


def test_compound_annually():
    """Annual compounding for exactly 365 days = simple interest for 1 year.

    I = P · (1 + r/1)^(1·1) − P = P · r = 1000 · 0.05 = 50 (exact).
    """
    principal = Decimal("1000")
    annual_rate = Decimal("0.05")
    days = 365

    result = InterestCalculator.calculate_compound_interest(
        principal, annual_rate, days, CompoundingPeriod.ANNUALLY
    )

    # For n=1, t=1 the formula collapses to P*r, which is exactly 50.
    assert result == pytest.approx(Decimal("50"), rel=Decimal("1e-9"))
