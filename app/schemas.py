# app/schemas.py
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID

# === User (DB → API) ===
class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    phone: Optional[str] = None
    is_company: bool = False
    company_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(min_length=8)
    confirm_password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_company: Optional[bool] = None
    company_name: Optional[str] = None
    password: Optional[str] = None

class UserOut(UserBase):
    id: UUID
    active: bool

    class Config:
        from_attributes = True  # pydantic v2 (antes orm_mode=True)
