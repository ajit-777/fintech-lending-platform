from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    phone: str
    password: str


class UserResponse(BaseModel):
    email: str
    phone: str
    role: str

    class Config:
        from_attributes = True
