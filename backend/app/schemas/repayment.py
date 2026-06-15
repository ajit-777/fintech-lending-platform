import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class RepaymentInstallmentResponse(BaseModel):
    id: uuid.UUID
    loan_id: uuid.UUID
    installment_number: int
    due_date: date
    emi_amount: float
    principal: float
    interest: float
    outstanding_principal: float
    status: str
    paid_at: Optional[datetime]
    paid_amount: Optional[float]

    class Config:
        from_attributes = True
