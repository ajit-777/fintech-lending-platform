from datetime import date, timedelta

import pytest

from app.models.loan_application import LoanApplication
from app.models.repayment import RepaymentInstallment
from app.services.overdue import mark_overdue


def _make_loan(db, late_payment_penalty_pct=2.0):
    loan = LoanApplication(
        user_id=__import__("uuid").uuid4(),
        amount=100000,
        tenure_months=12,
        purpose="test",
        cibil_score=750,
        monthly_income=50000,
        annual_interest_rate=10,
        processing_fee=1500,
        early_closure_fee_pct=2,
        late_payment_penalty_pct=late_payment_penalty_pct,
        status="disbursed",
    )
    db.add(loan)
    db.flush()
    return loan


def _make_installment(db, loan, due_date, status="pending"):
    inst = RepaymentInstallment(
        loan_id=loan.id,
        installment_number=1,
        due_date=due_date,
        emi_amount=9000,
        principal=8250,
        interest=750,
        outstanding_principal=91750,
        status=status,
    )
    db.add(inst)
    db.flush()
    return inst


def test_marks_past_due_installment_overdue(db_session):
    loan = _make_loan(db_session)
    inst = _make_installment(db_session, loan, due_date=date.today() - timedelta(days=10))
    db_session.commit()

    count = mark_overdue(db_session)

    assert count == 1
    db_session.refresh(inst)
    assert inst.status == "overdue"
    assert inst.penalty_amount > 0


def test_penalty_amount_calculation(db_session):
    loan = _make_loan(db_session, late_payment_penalty_pct=2.0)
    days_overdue = 30
    inst = _make_installment(db_session, loan, due_date=date.today() - timedelta(days=days_overdue))
    db_session.commit()

    mark_overdue(db_session)
    db_session.refresh(inst)

    expected = round(9000 * (2.0 / 100 / 365) * days_overdue, 2)
    assert float(inst.penalty_amount) == pytest.approx(expected, abs=0.01)


def test_does_not_touch_future_installments(db_session):
    loan = _make_loan(db_session)
    inst = _make_installment(db_session, loan, due_date=date.today() + timedelta(days=5))
    db_session.commit()

    count = mark_overdue(db_session)

    assert count == 0
    db_session.refresh(inst)
    assert inst.status == "pending"


def test_does_not_touch_paid_installments(db_session):
    loan = _make_loan(db_session)
    inst = _make_installment(db_session, loan, due_date=date.today() - timedelta(days=5), status="paid")
    db_session.commit()

    count = mark_overdue(db_session)

    assert count == 0
    db_session.refresh(inst)
    assert inst.status == "paid"


def test_does_not_double_mark_already_overdue(db_session):
    loan = _make_loan(db_session)
    inst = _make_installment(db_session, loan, due_date=date.today() - timedelta(days=5), status="overdue")
    db_session.commit()

    count = mark_overdue(db_session)

    assert count == 0
