from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.loan_application import LoanApplication
from app.models.repayment import RepaymentInstallment


def mark_overdue(db: Session) -> int:
    """
    Mark all pending installments whose due_date has passed as overdue
    and calculate the late payment penalty. Returns count of rows updated.
    """
    today = date.today()

    overdue_installments = (
        db.query(RepaymentInstallment)
        .join(LoanApplication, RepaymentInstallment.loan_id == LoanApplication.id)
        .filter(
            RepaymentInstallment.status == "pending",
            RepaymentInstallment.due_date < today,
        )
        .all()
    )

    for installment in overdue_installments:
        loan = installment.loan
        days_overdue = (today - installment.due_date).days
        daily_penalty_rate = float(loan.late_payment_penalty_pct) / 100 / 365
        penalty = round(float(installment.emi_amount) * daily_penalty_rate * days_overdue, 2)

        installment.status = "overdue"
        installment.penalty_amount = penalty

    if overdue_installments:
        db.commit()

    return len(overdue_installments)
