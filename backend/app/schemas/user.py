import uuid

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    phone: str
    password: str


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
