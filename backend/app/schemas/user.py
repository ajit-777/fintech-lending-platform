import re
import uuid

from pydantic import BaseModel, EmailStr, field_validator


# RBI Cybersecurity Framework for NBFCs (Dec 2022) requires:
# - Minimum 8 characters
# - Mix of uppercase, lowercase, digits, and special characters
_PASSWORD_MIN_LENGTH = 8
_INDIAN_MOBILE_RE = re.compile(r'^[6-9]\d{9}$')


class UserCreate(BaseModel):
    email: EmailStr
    phone: str
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        digits = re.sub(r'^\+91', '', v.strip())
        if not _INDIAN_MOBILE_RE.match(digits):
            raise ValueError(
                "Phone must be a valid 10-digit Indian mobile number (starting with 6–9)"
            )
        return digits

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        errors = []
        if len(v) < _PASSWORD_MIN_LENGTH:
            errors.append(f"at least {_PASSWORD_MIN_LENGTH} characters")
        if not re.search(r'[A-Z]', v):
            errors.append("one uppercase letter")
        if not re.search(r'[a-z]', v):
            errors.append("one lowercase letter")
        if not re.search(r'\d', v):
            errors.append("one digit")
        if not re.search(r'[!@#$%^&*(),.?\":{}|<>_\-\[\]\\/\'+~`=]', v):
            errors.append("one special character")
        if errors:
            raise ValueError("Password must contain " + ", ".join(errors))
        return v


class UserLogin(BaseModel):
    identifier: str  # email or phone number
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    phone: str
    role: str

    class Config:
        from_attributes = True
