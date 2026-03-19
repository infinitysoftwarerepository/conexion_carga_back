from __future__ import annotations

from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel

EstadoDashboard = Literal['publicados', 'activos', 'inactivos', 'eliminados']
PeriodoDashboard = Literal['mes', 'semana', 'anual']


class TarjetasResumenOut(BaseModel):
    viajes_publicados: int
    viajes_activos: int
    viajes_inactivos: int
    viajes_eliminados: int


class PuntoSerieDashboardOut(BaseModel):
    label: str
    value: int


class ResumenDashboardOut(BaseModel):
    periodo: PeriodoDashboard
    estado: EstadoDashboard
    tarjetas: TarjetasResumenOut
    serie: List[PuntoSerieDashboardOut]


class UltimoViajePublicadoOut(BaseModel):
    id: str
    origen: str
    destino: str
    valor: int
    estado: Literal['activo', 'inactivo']
    fecha_publicacion: datetime


class TopHistoricoDashboardOut(BaseModel):
    label: str
    secondary_label: str | None = None
    total: int
