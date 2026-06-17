import re
import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, field_validator

_PAN_RE = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
_PINCODE_RE = re.compile(r'^\d{6}$')
_IFSC_RE = re.compile(r'^[A-Z]{4}0[A-Z0-9]{6}$')


class KYCSubmit(BaseModel):
    pan_number: str
    date_of_birth: str  # YYYY-MM-DD
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    pincode: str

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, v: str) -> str:
        v = v.strip().upper()
        if not _PAN_RE.match(v):
            raise ValueError("Invalid PAN format. Must be 10 characters: AAAAA9999A")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: str) -> str:
        try:
            dob = date.fromisoformat(v)
        except ValueError:
            raise ValueError("date_of_birth must be in YYYY-MM-DD format")
        age = (date.today() - dob).days // 365
        if age < 18:
            raise ValueError("Applicant must be at least 18 years old")
        if age > 70:
            raise ValueError("Applicant must be under 70 years old")
        return v

    @field_validator("pincode")
    @classmethod
    def validate_pincode(cls, v: str) -> str:
        if not _PINCODE_RE.match(v.strip()):
            raise ValueError("Pincode must be exactly 6 digits")
        return v.strip()


class AadhaarOTPRequest(BaseModel):
    aadhaar_number: str

    @field_validator("aadhaar_number")
    @classmethod
    def validate_aadhaar(cls, v: str) -> str:
        digits = re.sub(r'\s', '', v)
        if not re.match(r'^\d{12}$', digits):
            raise ValueError("Aadhaar number must be exactly 12 digits")
        return digits


class AadhaarOTPConfirm(BaseModel):
    otp: str
    ref_id: str  # reference token returned by send-otp step


class KYCStatusOverride(BaseModel):
    kyc_status: str
    rejection_reason: Optional[str] = None

    @field_validator("kyc_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"verified", "rejected"}
        if v not in allowed:
            raise ValueError(f"kyc_status must be one of {allowed}")
        return v


class KYCProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    pan_number: Optional[str] = None
    pan_verified: bool
    pan_name: Optional[str] = None
    aadhaar_last4: Optional[str] = None
    aadhaar_verified: bool
    date_of_birth: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    kyc_status: str
    rejection_reason: Optional[str] = None
    submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None

    class Config:
        from_attributes = True
