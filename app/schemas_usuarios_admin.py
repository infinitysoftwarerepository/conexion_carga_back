from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


EstadoFiltroUsuarioAdmin = Literal['todos', 'habilitado', 'inhabilitado']
TipoFiltroUsuarioAdmin = Literal['todos', 'usuario', 'empresa', 'conductor', 'premium']


class UsuarioAdminOut(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    is_company: bool = False
    company_name: Optional[str] = None
    active: bool = True
    created_at: datetime
    points: int = 0
    is_premium: bool = False
    is_driver: bool = False
    rol_id: Optional[int] = None
    is_admin: bool = False
    referred_by_id: Optional[str] = None
    referred_by_email: Optional[str] = None


class ListaUsuariosAdminOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[UsuarioAdminOut]


class CrearUsuarioAdminIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=30)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: Optional[str] = Field(default=None, max_length=128)
    is_company: bool = False
    company_name: Optional[str] = Field(default=None, max_length=255)
    is_premium: bool = False
    is_driver: bool = False
    is_admin: bool = False
    active: bool = True
    referred_by_id: Optional[UUID] = None


class ActualizarUsuarioAdminIn(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    confirm_password: Optional[str] = Field(default=None, max_length=128)
    is_company: Optional[bool] = None
    company_name: Optional[str] = Field(default=None, max_length=255)
    is_premium: Optional[bool] = None
    is_driver: Optional[bool] = None
    is_admin: Optional[bool] = None
    active: Optional[bool] = None
    referred_by_id: Optional[UUID] = None


class CambiarEstadoUsuarioAdminIn(BaseModel):
    active: bool


class CambiarEstadoUsuarioAdminOut(BaseModel):
    ok: bool
    message: str
    user: UsuarioAdminOut
