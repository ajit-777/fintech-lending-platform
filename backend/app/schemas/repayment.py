import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


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


class RepaymentPaymentRequest(BaseModel):
    paid_amount: Optional[float] = Field(None, gt=0, description="Defaults to the EMI amount if not provided")
