from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


# ---------- Create ----------
class UserCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    is_company: bool = False
    company_name: Optional[str] = None
    password: str = Field(min_length=8)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password must match")
        return self


# ---------- Update ----------
class UserUpdate(BaseModel):
    # Todos los campos son opcionales para poder hacer “partial update”
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_company: Optional[bool] = None
    company_name: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)
    confirm_password: Optional[str] = None

    @model_validator(mode="after")
    def passwords_match(self):
        # Si van a cambiar la clave, deben venir ambos y ser iguales
        if (self.password is not None or self.confirm_password is not None) and (
            self.password != self.confirm_password
        ):
            raise ValueError("password and confirm_password must match")
        return self


# ---------- Out ----------
class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    is_company: bool
    company_name: Optional[str] = None
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2
