from app.services.interest_calculator import InterestCalculator, CompoundingPeriod

def test_compound_monthly():
    principal = Decimal("1000")
    annual_rate = Decimal("0.05")
    days = 30
    compounding = CompoundingPeriod.MONTHLY
    expected_interest = Decimal("4.175")
    calculated_interest = InterestCalculator.calculate_compound_interest(principal, annual_rate, days, compounding)
    assert calculated_interest == expected_interest

def test_compound_annually():
    principal = Decimal("1000")
    annual_rate = Decimal("0.05")
    days = 365
    compounding = CompoundingPeriod.ANNUALLY
    expected_interest = Decimal("50")
    calculated_interest = InterestCalculator.calculate_compound_interest(principal, annual_rate, days, compounding)
    assert calculated_interest == expected_interest
