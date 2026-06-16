import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class DisbursementCreate(BaseModel):
    bank_account_number: str = Field(..., min_length=6, max_length=34)
    ifsc_code: str = Field(..., min_length=11, max_length=11)
    reference_number: str = Field(..., min_length=3, max_length=100)

    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc(cls, v: str) -> str:
        v = v.strip().upper()
        if not (len(v) == 11 and v[:4].isalpha() and v[4] == "0" and v[5:].isalnum()):
            raise ValueError("Invalid IFSC code format")
        return v


class DisbursementResponse(BaseModel):
    id: uuid.UUID
    loan_id: uuid.UUID
    gross_amount: float
    net_amount: float
    bank_account_number: str  # masked, last 4 digits only
    ifsc_code: str
    reference_number: str
    status: str
    disbursed_at: datetime

    class Config:
        from_attributes = True

    @field_validator("bank_account_number", mode="before")
    @classmethod
    def mask_account_number(cls, v: str) -> str:
        if len(v) <= 4:
            return v
        return "X" * (len(v) - 4) + v[-4:]
