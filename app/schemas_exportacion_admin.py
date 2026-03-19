from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UsuarioAdminExportOut(BaseModel):
    id: str
    nombre_completo: str
    correo: str
    telefono: Optional[str] = None
    empresa: Optional[str] = None
    tipo: str
    estado: str
    puntos: int
    fecha_creacion: datetime


class ViajeAdminExportOut(BaseModel):
    id_viaje: str
    usuario: Optional[str] = None
    empresa: Optional[str] = None
    origen: str
    destino: str
    estado: str
    tipo_carga: Optional[str] = None
    valor: int
    fecha_creacion: Optional[datetime] = None


class ViajeEliminadoAdminExportOut(BaseModel):
    id_viaje: str
    usuario: Optional[str] = None
    empresa: Optional[str] = None
    origen: Optional[str] = None
    destino: Optional[str] = None
    causal_eliminacion: str
    observacion: Optional[str] = None
    fecha_creacion_viaje: Optional[datetime] = None
    fecha_eliminacion: datetime
