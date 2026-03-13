from __future__ import annotations

import calendar
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models
from app.db import get_db
from app.schemas_dashboard import (
    PuntoSerieDashboardOut,
    ResumenDashboardOut,
    TarjetasResumenOut,
    UltimoViajePublicadoOut,
)
from app.security import get_current_user

router = APIRouter(prefix='/api/admin/dashboard', tags=['Admin Dashboard'])

ROL_ADMINISTRADOR = 'Administrador'
EMAILS_ADMIN_FALLBACK = {
    'daniloramirez0818@gmail.com',
    'ddgaviriaz@unal.edu.co',
}
DIAS_SEMANA_CORTOS = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']
MESES_CORTOS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

EstadoDashboard = Literal['publicados', 'activos', 'inactivos', 'eliminados']
PeriodoDashboard = Literal['mes', 'semana', 'anual']


def _normalizar_email(email: str) -> str:
    return (email or '').strip().lower()


def _obtener_emails_admin_configurados() -> set[str]:
    raw = os.getenv('WEB_ADMIN_EMAILS', '')
    return {email.strip().lower() for email in raw.split(',') if email.strip()}


def _usuario_tiene_rol_admin_en_bd(
    db: Session,
    user_id: UUID | str,
) -> Optional[bool]:
    try:
        estructura = db.execute(
            text(
                """
                SELECT
                    EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'conexion_carga'
                          AND table_name = 'rol'
                    ) AS tiene_tabla_rol,
                    EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = 'conexion_carga'
                          AND table_name = 'users'
                          AND column_name = 'rol_id'
                    ) AS tiene_columna_rol_id
                """
            )
        ).mappings().first()

        if not estructura:
            return None

        if not estructura['tiene_tabla_rol'] or not estructura['tiene_columna_rol_id']:
            return None

        rol_nombre = db.execute(
            text(
                """
                SELECT r.nombre
                FROM conexion_carga.users u
                JOIN conexion_carga.rol r
                  ON r.id = u.rol_id
                WHERE u.id = CAST(:user_id AS uuid)
                LIMIT 1
                """
            ),
            {'user_id': str(user_id)},
        ).scalar()

        if not rol_nombre:
            return False

        return str(rol_nombre).strip().lower() == ROL_ADMINISTRADOR.lower()
    except SQLAlchemyError:
        return None


def _usuario_es_admin(db: Session, email: str, user_id: UUID | str) -> bool:
    evaluacion_rol = _usuario_tiene_rol_admin_en_bd(db=db, user_id=user_id)
    if evaluacion_rol is not None:
        return evaluacion_rol

    emails_admin = _obtener_emails_admin_configurados()
    if not emails_admin:
        emails_admin = EMAILS_ADMIN_FALLBACK

    return _normalizar_email(email) in emails_admin


def _asegurar_usuario_admin(
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
) -> models.User:
    if not bool(getattr(current, 'active', False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Usuario inactivo. No tiene acceso al panel administrativo.',
        )

    if not _usuario_es_admin(db=db, email=str(current.email), user_id=current.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='El usuario no tiene permisos de Administrador.',
        )

    return current


def _normalizar_bucket_fecha(bucket: datetime) -> datetime:
    if bucket.tzinfo is None:
        return bucket.replace(tzinfo=timezone.utc)
    return bucket.astimezone(timezone.utc)


def _obtener_rango_periodo(
    periodo: PeriodoDashboard,
    ahora_utc: datetime,
) -> tuple[datetime, datetime]:
    if periodo == 'semana':
        inicio = (ahora_utc - timedelta(days=ahora_utc.weekday())).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        fin = inicio + timedelta(days=7)
        return inicio, fin

    if periodo == 'mes':
        inicio = ahora_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if inicio.month == 12:
            fin = inicio.replace(year=inicio.year + 1, month=1)
        else:
            fin = inicio.replace(month=inicio.month + 1)
        return inicio, fin

    inicio = ahora_utc.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    fin = inicio.replace(year=inicio.year + 1)
    return inicio, fin


def _filtro_no_eliminado() -> object:
    return text(
        """
        NOT EXISTS (
            SELECT 1
            FROM conexion_carga.carga_eliminada ce
            WHERE ce.carga_id = conexion_carga.carga.id
        )
        """
    )


def _filtros_carga_dashboard(
    estado: EstadoDashboard,
    inicio: datetime,
    fin: datetime,
) -> list:
    filtros = [
        models.Cargo.estado == 'publicado',
        models.Cargo.created_at >= inicio,
        models.Cargo.created_at < fin,
        _filtro_no_eliminado(),
    ]

    if estado == 'activos':
        filtros.append(models.Cargo.activo.is_(True))
    elif estado == 'inactivos':
        filtros.append(models.Cargo.activo.is_(False))

    return filtros


def _contar_carga_dashboard(
    db: Session,
    inicio: datetime,
    fin: datetime,
    estado: EstadoDashboard,
) -> int:
    filtros = _filtros_carga_dashboard(estado=estado, inicio=inicio, fin=fin)
    total = db.query(func.count(models.Cargo.id)).filter(*filtros).scalar() or 0
    return int(total)


def _contar_eliminados_dashboard(
    db: Session,
    inicio: datetime,
    fin: datetime,
) -> int:
    total = db.execute(
        text(
            """
            SELECT COUNT(DISTINCT ce.carga_id) AS total
            FROM conexion_carga.carga_eliminada ce
            WHERE ce.eliminado_en >= :inicio
              AND ce.eliminado_en < :fin
            """
        ),
        {'inicio': inicio, 'fin': fin},
    ).scalar()

    return int(total or 0)


def _obtener_mapa_serie_carga(
    db: Session,
    inicio: datetime,
    fin: datetime,
    estado: EstadoDashboard,
    granularidad: Literal['dia', 'mes'],
) -> dict[datetime, int]:
    bucket_expr = (
        func.date_trunc('month', models.Cargo.created_at)
        if granularidad == 'mes'
        else func.date_trunc('day', models.Cargo.created_at)
    )
    filtros = _filtros_carga_dashboard(estado=estado, inicio=inicio, fin=fin)

    filas = (
        db.query(bucket_expr.label('bucket'), func.count(models.Cargo.id).label('total'))
        .filter(*filtros)
        .group_by(bucket_expr)
        .all()
    )

    mapa: dict[datetime, int] = {}
    for fila in filas:
        bucket = _normalizar_bucket_fecha(fila.bucket)
        mapa[bucket] = int(fila.total or 0)

    return mapa


def _obtener_mapa_serie_eliminados(
    db: Session,
    inicio: datetime,
    fin: datetime,
    granularidad: Literal['dia', 'mes'],
) -> dict[datetime, int]:
    if granularidad == 'mes':
        consulta = text(
            """
            SELECT
                date_trunc('month', ce.eliminado_en) AS bucket,
                COUNT(DISTINCT ce.carga_id) AS total
            FROM conexion_carga.carga_eliminada ce
            WHERE ce.eliminado_en >= :inicio
              AND ce.eliminado_en < :fin
            GROUP BY 1
            """
        )
    else:
        consulta = text(
            """
            SELECT
                date_trunc('day', ce.eliminado_en) AS bucket,
                COUNT(DISTINCT ce.carga_id) AS total
            FROM conexion_carga.carga_eliminada ce
            WHERE ce.eliminado_en >= :inicio
              AND ce.eliminado_en < :fin
            GROUP BY 1
            """
        )

    filas = db.execute(
        consulta,
        {'inicio': inicio, 'fin': fin},
    ).mappings().all()

    mapa: dict[datetime, int] = {}
    for fila in filas:
        bucket = fila['bucket']
        if not bucket:
            continue
        bucket_normalizado = _normalizar_bucket_fecha(bucket)
        mapa[bucket_normalizado] = int(fila['total'] or 0)

    return mapa


def _sumar_mapas_series(*mapas: dict[datetime, int]) -> dict[datetime, int]:
    acumulado: dict[datetime, int] = {}
    for mapa in mapas:
        for bucket, valor in mapa.items():
            acumulado[bucket] = int(acumulado.get(bucket, 0)) + int(valor or 0)
    return acumulado


def _obtener_mapa_serie_dashboard(
    db: Session,
    inicio: datetime,
    fin: datetime,
    estado: EstadoDashboard,
    granularidad: Literal['dia', 'mes'],
) -> dict[datetime, int]:
    if estado == 'activos':
        return _obtener_mapa_serie_carga(
            db=db,
            inicio=inicio,
            fin=fin,
            estado='activos',
            granularidad=granularidad,
        )

    if estado == 'inactivos':
        return _obtener_mapa_serie_carga(
            db=db,
            inicio=inicio,
            fin=fin,
            estado='inactivos',
            granularidad=granularidad,
        )

    if estado == 'eliminados':
        return _obtener_mapa_serie_eliminados(
            db=db,
            inicio=inicio,
            fin=fin,
            granularidad=granularidad,
        )

    mapa_publicados_carga = _obtener_mapa_serie_carga(
        db=db,
        inicio=inicio,
        fin=fin,
        estado='publicados',
        granularidad=granularidad,
    )
    mapa_eliminados = _obtener_mapa_serie_eliminados(
        db=db,
        inicio=inicio,
        fin=fin,
        granularidad=granularidad,
    )

    return _sumar_mapas_series(mapa_publicados_carga, mapa_eliminados)


def _obtener_tarjetas_resumen(
    db: Session,
    inicio: datetime,
    fin: datetime,
) -> TarjetasResumenOut:
    viajes_activos = _contar_carga_dashboard(
        db=db,
        inicio=inicio,
        fin=fin,
        estado='activos',
    )
    viajes_inactivos = _contar_carga_dashboard(
        db=db,
        inicio=inicio,
        fin=fin,
        estado='inactivos',
    )
    viajes_eliminados = _contar_eliminados_dashboard(db=db, inicio=inicio, fin=fin)
    viajes_publicados = viajes_activos + viajes_inactivos + viajes_eliminados

    return TarjetasResumenOut(
        viajes_publicados=int(viajes_publicados),
        viajes_activos=int(viajes_activos),
        viajes_inactivos=int(viajes_inactivos),
        viajes_eliminados=int(viajes_eliminados),
    )


def _serie_ceros(labels: list[str]) -> list[PuntoSerieDashboardOut]:
    return [PuntoSerieDashboardOut(label=label, value=0) for label in labels]


def _obtener_serie_semana(
    db: Session,
    ahora_utc: datetime,
    estado: EstadoDashboard,
) -> list[PuntoSerieDashboardOut]:
    inicio, fin = _obtener_rango_periodo('semana', ahora_utc)
    mapa_buckets = _obtener_mapa_serie_dashboard(
        db=db,
        inicio=inicio,
        fin=fin,
        estado=estado,
        granularidad='dia',
    )

    mapa: dict[datetime.date, int] = {}
    for bucket, total in mapa_buckets.items():
        mapa[bucket.date()] = int(total or 0)

    serie: list[PuntoSerieDashboardOut] = []
    for i in range(7):
        fecha = inicio + timedelta(days=i)
        serie.append(
            PuntoSerieDashboardOut(
                label=DIAS_SEMANA_CORTOS[i],
                value=mapa.get(fecha.date(), 0),
            )
        )

    return serie


def _obtener_serie_mes(
    db: Session,
    ahora_utc: datetime,
    estado: EstadoDashboard,
) -> list[PuntoSerieDashboardOut]:
    inicio, fin = _obtener_rango_periodo('mes', ahora_utc)
    dias_mes = calendar.monthrange(inicio.year, inicio.month)[1]

    mapa_buckets = _obtener_mapa_serie_dashboard(
        db=db,
        inicio=inicio,
        fin=fin,
        estado=estado,
        granularidad='dia',
    )

    mapa: dict[int, int] = {}
    for bucket, total in mapa_buckets.items():
        mapa[bucket.day] = int(total or 0)

    serie: list[PuntoSerieDashboardOut] = []
    for dia in range(1, dias_mes + 1):
        serie.append(
            PuntoSerieDashboardOut(
                label=f'{dia:02d}',
                value=mapa.get(dia, 0),
            )
        )

    return serie


def _obtener_serie_anual(
    db: Session,
    ahora_utc: datetime,
    estado: EstadoDashboard,
) -> list[PuntoSerieDashboardOut]:
    inicio, fin = _obtener_rango_periodo('anual', ahora_utc)
    mapa_buckets = _obtener_mapa_serie_dashboard(
        db=db,
        inicio=inicio,
        fin=fin,
        estado=estado,
        granularidad='mes',
    )

    mapa: dict[int, int] = {}
    for bucket, total in mapa_buckets.items():
        mapa[bucket.month] = int(total or 0)

    serie: list[PuntoSerieDashboardOut] = []
    for mes in range(1, 13):
        serie.append(
            PuntoSerieDashboardOut(
                label=MESES_CORTOS[mes - 1],
                value=mapa.get(mes, 0),
            )
        )

    return serie


def _obtener_valor_entero(valor: object) -> int:
    if valor is None:
        return 0

    try:
        return int(Decimal(valor))
    except Exception:
        return 0


@router.get('/resumen', response_model=ResumenDashboardOut)
def obtener_resumen_dashboard(
    periodo: PeriodoDashboard = Query(default='mes', pattern='^(mes|semana|anual)$'),
    estado: EstadoDashboard = Query(
        default='publicados',
        pattern='^(publicados|activos|inactivos|eliminados)$',
    ),
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    ahora_utc = datetime.now(timezone.utc)
    inicio, fin = _obtener_rango_periodo(periodo, ahora_utc)

    if periodo == 'semana':
        serie = _obtener_serie_semana(db, ahora_utc, estado)
    elif periodo == 'anual':
        serie = _obtener_serie_anual(db, ahora_utc, estado)
    else:
        serie = _obtener_serie_mes(db, ahora_utc, estado)

    tarjetas = _obtener_tarjetas_resumen(db, inicio=inicio, fin=fin)

    return ResumenDashboardOut(
        periodo=periodo,
        estado=estado,
        tarjetas=tarjetas,
        serie=serie,
    )


@router.get('/ultimos-viajes', response_model=list[UltimoViajePublicadoOut])
def obtener_ultimos_viajes_publicados(
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    cargas = (
        db.query(models.Cargo)
        .filter(models.Cargo.estado == 'publicado')
        .order_by(models.Cargo.created_at.desc())
        .limit(limit)
        .all()
    )

    resultados: list[UltimoViajePublicadoOut] = []
    for carga in cargas:
        created_at = carga.created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        resultados.append(
            UltimoViajePublicadoOut(
                id=str(carga.id),
                origen=str(carga.origen or ''),
                destino=str(carga.destino or ''),
                valor=_obtener_valor_entero(carga.valor),
                estado='activo' if bool(carga.activo) else 'inactivo',
                fecha_publicacion=created_at or datetime.now(timezone.utc),
            )
        )

    return resultados
