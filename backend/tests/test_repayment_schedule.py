import uuid
from datetime import date

from app.services import repayment_schedule


def test_generates_correct_number_of_installments():
    installments = repayment_schedule.generate(
        loan_id=uuid.uuid4(), principal=100000, tenure_months=12,
        approval_date=date(2026, 1, 1), annual_interest_rate=12.0,
    )
    assert len(installments) == 12
    assert [i.installment_number for i in installments] == list(range(1, 13))


def test_emi_amount_matches_known_value():
    # 1,00,000 at 12% p.a. for 12 months -> EMI ~= 8,884.88
    installments = repayment_schedule.generate(
        loan_id=uuid.uuid4(), principal=100000, tenure_months=12,
        approval_date=date(2026, 1, 1), annual_interest_rate=12.0,
    )
    assert abs(float(installments[0].emi_amount) - 8884.88) < 1


def test_outstanding_principal_reaches_zero_at_final_installment():
    installments = repayment_schedule.generate(
        loan_id=uuid.uuid4(), principal=100000, tenure_months=12,
        approval_date=date(2026, 1, 1), annual_interest_rate=12.0,
    )
    assert float(installments[-1].outstanding_principal) == 0.0


def test_total_principal_paid_equals_loan_amount():
    principal = 250000
    installments = repayment_schedule.generate(
        loan_id=uuid.uuid4(), principal=principal, tenure_months=24,
        approval_date=date(2026, 1, 1), annual_interest_rate=14.0,
    )
    total_principal_paid = sum(float(i.principal) for i in installments)
    assert abs(total_principal_paid - principal) < 1  # rounding tolerance


def test_due_dates_are_monthly_and_sequential():
    installments = repayment_schedule.generate(
        loan_id=uuid.uuid4(), principal=50000, tenure_months=3,
        approval_date=date(2026, 1, 15), annual_interest_rate=10.0,
    )
    assert installments[0].due_date == date(2026, 2, 15)
    assert installments[1].due_date == date(2026, 3, 15)
    assert installments[2].due_date == date(2026, 4, 15)


def test_interest_decreases_each_month_on_reducing_balance():
    installments = repayment_schedule.generate(
        loan_id=uuid.uuid4(), principal=100000, tenure_months=12,
        approval_date=date(2026, 1, 1), annual_interest_rate=12.0,
    )
    interests = [float(i.interest) for i in installments]
    assert all(interests[i] > interests[i + 1] for i in range(len(interests) - 1))
