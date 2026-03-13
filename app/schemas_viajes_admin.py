from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


EstadoViajeAdmin = Literal['activo', 'inactivo']
FiltroEstadoViajeAdmin = Literal['activo', 'inactivo', 'todos']


class ViajeAdminOut(BaseModel):
    id: str
    empresa_id: Optional[str] = None
    comercial_id: str
    origen: str
    destino: str
    tipo_carga: str
    peso: float
    valor: int
    comercial: Optional[str] = None
    contacto: Optional[str] = None
    observaciones: Optional[str] = None
    conductor: Optional[str] = None
    tipo_vehiculo: Optional[str] = None
    premium_trip: bool = False
    duration_hours: int = 24
    duracion_publicacion: int = 24
    duracion_publicacion_unidad: Literal['minutos', 'horas'] = 'horas'
    estado: EstadoViajeAdmin
    created_at: datetime
    fecha_publicacion: datetime
    expires_at: Optional[datetime] = None
    updated_at: datetime


class ListaViajesAdminOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ViajeAdminOut]


class CausalEliminacionOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None


class ActualizarViajeAdminIn(BaseModel):
    empresa_id: Optional[UUID] = None
    origen: Optional[str] = None
    destino: Optional[str] = None
    tipo_carga: Optional[str] = None
    peso: Optional[float] = Field(default=None, ge=0)
    valor: Optional[int] = Field(default=None, ge=0)
    comercial: Optional[str] = None
    contacto: Optional[str] = None
    observaciones: Optional[str] = None
    conductor: Optional[str] = None
    tipo_vehiculo: Optional[str] = None
    premium_trip: Optional[bool] = None
    duration_hours: Optional[int] = Field(default=None, ge=1, le=168)


class EliminarViajeAdminIn(BaseModel):
    causal_id: int = Field(ge=1)
    observacion: Optional[str] = None


class EliminarViajeAdminOut(BaseModel):
    ok: bool
    message: str
    carga_eliminada_id: str


class ViajeEliminadoOut(BaseModel):
    id: str
    carga_id: str
    causal_id: int
    causal_nombre: str
    observacion: Optional[str] = None
    eliminado_por: Optional[str] = None
    eliminado_en: datetime
    origen: Optional[str] = None
    destino: Optional[str] = None
    valor: int = 0


class ListaViajesEliminadosOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ViajeEliminadoOut]


class ViajeEliminadoDetalleOut(ViajeEliminadoOut):
    tipo_carga: Optional[str] = None
    estado: Optional[str] = None
    fecha_publicacion: Optional[datetime] = None
    snapshot_json: Optional[dict[str, Any]] = None
