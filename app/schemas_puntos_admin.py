from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UsuarioPuntosAdminOut(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    company_name: Optional[str] = None
    active: bool = True
    created_at: datetime
    points: int = 0
    referred_count: int = 0


class ListaUsuariosPuntosAdminOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[UsuarioPuntosAdminOut]


class ActualizarPuntosAdminIn(BaseModel):
    points: int = Field(ge=0, le=1000000)


class ActualizarPuntosAdminOut(BaseModel):
    ok: bool
    message: str
    user: UsuarioPuntosAdminOut


class UsuarioReferidoAdminOut(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    company_name: Optional[str] = None
    active: bool = True
    created_at: datetime


class ListaReferidosAdminOut(BaseModel):
    total: int
    items: list[UsuarioReferidoAdminOut]


class QuitarReferidoAdminOut(BaseModel):
    ok: bool
    message: str
    parent_user: UsuarioPuntosAdminOut
    removed_referred_id: str
