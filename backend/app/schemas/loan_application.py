import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class LoanApplicationCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Loan amount in INR")
    tenure_months: int = Field(..., gt=0, le=360, description="Repayment period in months")
    purpose: str = Field(..., min_length=3, max_length=255)
    notes: Optional[str] = None


class LoanApplicationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    amount: float
    tenure_months: int
    purpose: str
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
