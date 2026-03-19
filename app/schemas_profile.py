from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class PerfilActualOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    full_name: str
    email: EmailStr
    phone: str | None = None
    is_company: bool = False
    company_name: str | None = None
    active: bool = False
    created_at: datetime
    foto: str | None = None
    foto_url: str | None = None


class ActualizarPerfilIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    company_name: str | None = Field(default=None, max_length=255)


class CambiarPasswordPerfilIn(BaseModel):
    password_actual: str = Field(min_length=1)
    nueva_password: str = Field(min_length=8, max_length=255)
    confirmar_nueva_password: str = Field(min_length=8, max_length=255)


class MensajePerfilOut(BaseModel):
    message: str
