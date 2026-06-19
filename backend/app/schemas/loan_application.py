import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LoanApplicationCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Loan amount in INR")
    tenure_months: int = Field(..., gt=0, le=360, description="Repayment period in months")
    purpose: str = Field(..., min_length=3, max_length=255)
    cibil_score: int = Field(..., ge=300, le=900, description="Applicant's CIBIL score (300–900)")
    monthly_income: float = Field(..., gt=0, description="Applicant's monthly income in INR")
    bank_account_number: str = Field(..., min_length=6, max_length=34, description="Borrower's bank account number")
    ifsc_code: str = Field(..., min_length=11, max_length=11, description="IFSC code of the bank branch")
    notes: Optional[str] = None

    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc(cls, v: str) -> str:
        v = v.strip().upper()
        if not (len(v) == 11 and v[:4].isalpha() and v[4] == "0" and v[5:].isalnum()):
            raise ValueError("Invalid IFSC code (format: AAAA0XXXXXX)")
        return v


class LoanApplicationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    amount: float
    tenure_months: int
    purpose: str
    loan_type: str
    cibil_score: int
    monthly_income: float
    annual_interest_rate: float
    processing_fee: float
    early_closure_fee_pct: float
    late_payment_penalty_pct: float
    status: str
    rejection_reason: Optional[str]
    reviewed_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    bank_account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    agreement_accepted: bool = False
    agreement_accepted_at: Optional[datetime] = None
    bank_account_verified: bool = False
    bank_account_holder_name: Optional[str] = None
    penny_drop_name_match_score: Optional[float] = None
    bank_account_override: bool = False
    user_email: Optional[str] = None
    user_phone: Optional[str] = None

    class Config:
        from_attributes = True


class LoanReviewRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Reason for approval or rejection")
