from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID

class UserCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    is_company: bool = False
    company_name: Optional[str] = None
    password: str = Field(min_length=8)
    confirm_password: str

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    is_company: bool
    company_name: Optional[str] = None
    active: bool

    class Config:
        from_attributes = True  # Pydantic v2
