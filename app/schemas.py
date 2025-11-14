# app/schemas.py
from __future__ import annotations
from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# ========= USERS =========

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
    referrer_email: Optional[EmailStr] = None

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
    points: int = 0
    is_premium: bool = False

    class Config:
        from_attributes = True

# ========= AUTH =========

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserOut] = None

# ========= CARGA =========

class CargoBase(BaseModel):
    empresa_id: Optional[UUID] = None
    origen: str
    destino: str
    tipo_carga: str
    peso: float
    valor: int
    # extras
    comercial: Optional[str] = None
    contacto: Optional[str] = None
    observaciones: Optional[str] = None
    conductor: Optional[str] = None
    # vehiculo_id: Optional[str] = None  # ❌ eliminado
    tipo_vehiculo: Optional[str] = None

    # duración en horas
    duration_hours: int = Field(default=24, ge=1, le=168)

class CargoCreate(CargoBase):
    pass

class CargoUpdate(BaseModel):
    empresa_id: Optional[UUID] = None
    origen: Optional[str] = None
    destino: Optional[str] = None
    tipo_carga: Optional[str] = None
    peso: Optional[float] = None
    valor: Optional[int] = None
    comercial: Optional[str] = None
    contacto: Optional[str] = None
    observaciones: Optional[str] = None
    conductor: Optional[str] = None
    tipo_vehiculo: Optional[str] = None
    duration_hours: Optional[int] = Field(default=None, ge=1, le=168)

class CargoOut(CargoBase):
    id: UUID
    comercial_id: UUID
    estado: str
    activo: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ========= CATÁLOGOS =========

class CatalogoIn(BaseModel):
    nombre: str

class CatalogoOut(BaseModel):
    id: int
    nombre: str
    activo: bool

    class Config:
        from_attributes = True
