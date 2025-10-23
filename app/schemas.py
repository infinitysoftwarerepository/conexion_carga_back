# app/schemas.py
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID

# ===== Carga (nuevo) =====
from datetime import datetime

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
    # ⬇️ NUEVO: email del referidor (opcional)
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
    # ⬇️ NUEVO: exponer puntos e is_premium
    points: int = 0
    is_premium: bool = False

    class Config:
        from_attributes = True  # pydantic v2 (antes orm_mode=True)



class CargoBase(BaseModel):
    empresa_id: Optional[UUID] = None
    origen: str
    destino: str
    tipo_carga: str
    peso: float
    valor: int
    conductor: Optional[str] = None
    vehiculo_id: Optional[str] = None
    fecha_salida: datetime
    fecha_llegada_estimada: Optional[datetime] = None
    premium_trip: bool = False   # ⬅ por defecto false

class CargoCreate(CargoBase):
    pass  # todo lo necesario llega del front

class CargoOut(CargoBase):
    id: UUID
    comercial_id: UUID
    active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
