import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PricingConfigResponse(BaseModel):
    id: uuid.UUID
    cibil_min: int
    cibil_max: int
    tier_label: str
    annual_interest_rate: float
    processing_fee_pct: float
    origination_fee_pct: float
    early_closure_fee_pct: float
    late_payment_penalty_pct: float
    updated_at: datetime

    class Config:
        from_attributes = True


class PricingConfigUpdate(BaseModel):
    annual_interest_rate: float = Field(..., gt=0, le=100)
    processing_fee_pct: float = Field(..., ge=0, le=10)
    origination_fee_pct: float = Field(..., ge=0, le=10)
    early_closure_fee_pct: float = Field(..., ge=0, le=10)
    late_payment_penalty_pct: float = Field(..., ge=0, le=10)
