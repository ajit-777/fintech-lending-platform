import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoanApplicationCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Loan amount in INR")
    tenure_months: int = Field(..., gt=0, le=360, description="Repayment period in months")
    purpose: str = Field(..., min_length=3, max_length=255)
    cibil_score: int = Field(..., ge=300, le=900, description="Applicant's CIBIL score (300–900)")
    monthly_income: float = Field(..., gt=0, description="Applicant's monthly income in INR")
    notes: Optional[str] = None


class LoanApplicationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    amount: float
    tenure_months: int
    purpose: str
    cibil_score: int
    monthly_income: float
    status: str
    rejection_reason: Optional[str]
    reviewed_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoanReviewRequest(BaseModel):
    reason: str = Field(..., min_length=5, description="Reason for approval or rejection")
