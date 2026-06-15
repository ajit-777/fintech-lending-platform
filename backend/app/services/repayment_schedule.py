from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List

from app.models.repayment import RepaymentInstallment


def generate(loan_id, principal: float, tenure_months: int, approval_date: date, annual_interest_rate: float) -> List[RepaymentInstallment]:
    r = annual_interest_rate / 12 / 100
    emi = principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)
    emi = round(emi, 2)

    installments = []
    outstanding = principal

    for i in range(1, tenure_months + 1):
        interest = round(outstanding * r, 2)
        principal_component = round(emi - interest, 2)

        # Adjust final installment for rounding drift
        if i == tenure_months:
            principal_component = round(outstanding, 2)
            emi_amount = round(principal_component + interest, 2)
        else:
            emi_amount = emi

        outstanding = round(outstanding - principal_component, 2)
        due_date = approval_date + relativedelta(months=i)

        installments.append(RepaymentInstallment(
            loan_id=loan_id,
            installment_number=i,
            due_date=due_date,
            emi_amount=emi_amount,
            principal=principal_component,
            interest=interest,
            outstanding_principal=max(outstanding, 0),
        ))

    return installments
