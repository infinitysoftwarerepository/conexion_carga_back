from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.db import get_db
from app.routers.dashboard_admin import _asegurar_usuario_admin
from app.schemas_exportacion_admin import (
    ViajeAdminExportOut,
    ViajeEliminadoAdminExportOut,
)
from app.schemas_viajes_admin import (
    ActualizarViajeAdminIn,
    CausalEliminacionOut,
    EliminarViajeAdminIn,
    EliminarViajeAdminOut,
    FiltroEstadoViajeAdmin,
    ListaViajesAdminOut,
    ListaViajesEliminadosOut,
    ViajeAdminOut,
    ViajeEliminadoDetalleOut,
    ViajeEliminadoOut,
)

router = APIRouter(prefix='/api/admin', tags=['Admin Viajes'])

MINIMO_OBSERVACION_OTRO = 8
MAXIMO_OBSERVACION = 2000


def _normalizar_nombre_causal(nombre: str | None) -> str:
    texto = str(nombre or '').strip().lower()
    if texto.startswith('otro') or texto.startswith('otra'):
        return 'Otra'
    return str(nombre or '').strip()


def _es_causal_observacion_libre(nombre: str | None) -> bool:
    texto = str(nombre or '').strip().lower()
    return texto.startswith('otro') or texto.startswith('otra')


def _normalizar_fecha(fecha: datetime | None) -> datetime:
    if fecha is None:
        return datetime.now(timezone.utc)
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(timezone.utc)


def _parsear_fecha_iso(valor: object) -> datetime | None:
    if valor is None:
        return None

    if isinstance(valor, datetime):
        return _normalizar_fecha(valor)

    texto = str(valor).strip()
    if not texto:
        return None

    try:
        fecha = datetime.fromisoformat(texto.replace('Z', '+00:00'))
    except ValueError:
        return None

    return _normalizar_fecha(fecha)


def _parsear_fecha_filtro(
    valor: str | None,
    *,
    nombre_parametro: str,
    fin_de_dia: bool = False,
) -> datetime | None:
    texto = str(valor or '').strip()
    if not texto:
        return None

    try:
        if len(texto) == 10:
            fecha_base = date.fromisoformat(texto)
            fecha = datetime.combine(fecha_base, datetime.min.time()).replace(
                tzinfo=timezone.utc
            )
            if fin_de_dia:
                fecha = fecha + timedelta(days=1) - timedelta(microseconds=1)
            return fecha

        fecha = datetime.fromisoformat(texto.replace('Z', '+00:00'))
        return _normalizar_fecha(fecha)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f'El parámetro "{nombre_parametro}" tiene formato inválido. '
                'Usa ISO 8601 o YYYY-MM-DD.'
            ),
        )


def _normalizar_snapshot_json(snapshot_json: object) -> dict[str, Any]:
    if isinstance(snapshot_json, dict):
        return snapshot_json

    if isinstance(snapshot_json, str):
        try:
            data = json.loads(snapshot_json)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return {}

    return {}


def _coalescer_texto(*valores: object) -> str | None:
    for valor in valores:
        if valor is None:
            continue

        texto = str(valor).strip()
        if texto:
            return texto

    return None


def _resolver_usuario_publicador(*valores: object) -> str | None:
    return _coalescer_texto(*valores)


def _resolver_empresa_publicadora(*valores: object) -> str | None:
    return _coalescer_texto(*valores)


def _resolver_estado_viaje(
    estado_snapshot: object,
    carga_activo: object,
    carga_estado: object,
) -> str | None:
    estado = _coalescer_texto(estado_snapshot)
    if estado:
        estado_lower = estado.lower()
        if estado_lower in {'activo', 'inactivo'}:
            return estado_lower
        if estado_lower == 'publicado':
            return 'activo'
        return estado

    if carga_activo is True:
        return 'activo'
    if carga_activo is False:
        return 'inactivo'

    estado_carga = _coalescer_texto(carga_estado)
    if estado_carga:
        estado_carga_lower = estado_carga.lower()
        if estado_carga_lower in {'activo', 'inactivo'}:
            return estado_carga_lower
        if estado_carga_lower == 'publicado':
            return 'activo'
        return estado_carga

    return None


def _obtener_valor_entero(valor: object) -> int:
    if valor is None:
        return 0

    try:
        return int(Decimal(valor))
    except Exception:
        return 0


def _obtener_peso_flotante(peso: object) -> float:
    if peso is None:
        return 0.0

    try:
        return float(Decimal(peso))
    except Exception:
        return 0.0


def _obtener_horas_duracion(intervalo: object) -> int:
    if not intervalo:
        return 24

    try:
        if isinstance(intervalo, timedelta):
            return max(1, int(intervalo.total_seconds() // 3600))
        return 24
    except Exception:
        return 24


def _asegurar_tablas_eliminacion(db: Session) -> None:
    estructura = db.execute(
        text(
            """
            SELECT
                EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'conexion_carga'
                      AND table_name = 'causales_eliminacion'
                ) AS tiene_causales,
                EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'conexion_carga'
                      AND table_name = 'carga_eliminada'
                ) AS tiene_historial
            """
        )
    ).mappings().first()

    if not estructura:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='No fue posible validar la estructura administrativa de eliminacion.',
        )

    if not estructura['tiene_causales'] or not estructura['tiene_historial']:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                'La estructura administrativa de eliminacion no existe. '
                'Ejecuta primero el script scripts_sql/02_eliminacion_controlada_viajes.sql.'
            ),
        )


def _sincronizar_vigencia_publicaciones(db: Session) -> None:
    actualizados = db.execute(
        text(
            """
            UPDATE conexion_carga.carga c
            SET
                activo = FALSE,
                updated_at = NOW()
            WHERE c.estado = 'publicado'
              AND c.activo = TRUE
              AND c.created_at IS NOT NULL
              AND c.duracion_publicacion IS NOT NULL
              AND (c.created_at + c.duracion_publicacion) <= NOW()
            """
        )
    ).rowcount

    if actualizados and int(actualizados) > 0:
        db.commit()


def _serializar_viaje(carga: models.Cargo) -> ViajeAdminOut:
    created_at = _normalizar_fecha(carga.created_at)
    duration_hours = _obtener_horas_duracion(carga.duracion_publicacion)
    expires_at = created_at + timedelta(hours=duration_hours)

    return ViajeAdminOut(
        id=str(carga.id),
        empresa_id=str(carga.empresa_id) if carga.empresa_id else None,
        comercial_id=str(carga.comercial_id),
        origen=str(carga.origen or ''),
        destino=str(carga.destino or ''),
        tipo_carga=str(carga.tipo_carga or ''),
        peso=_obtener_peso_flotante(carga.peso),
        valor=_obtener_valor_entero(carga.valor),
        comercial=str(carga.comercial or '') or None,
        contacto=str(carga.contacto or '') or None,
        observaciones=str(carga.observaciones or '') or None,
        conductor=str(carga.conductor or '') or None,
        tipo_vehiculo=str(carga.tipo_vehiculo or '') or None,
        premium_trip=bool(carga.premium_trip),
        duration_hours=duration_hours,
        duracion_publicacion=duration_hours,
        duracion_publicacion_unidad='horas',
        estado='activo' if bool(carga.activo) else 'inactivo',
        created_at=created_at,
        fecha_publicacion=created_at,
        expires_at=expires_at,
        updated_at=_normalizar_fecha(carga.updated_at),
    )


def _snapshot_viaje(carga: models.Cargo) -> dict:
    serializado = _serializar_viaje(carga)
    return serializado.model_dump(mode='json')


def _serializar_viaje_eliminado_desde_fila(
    fila: Any,
    *,
    incluir_snapshot: bool = False,
) -> ViajeEliminadoOut | ViajeEliminadoDetalleOut:
    snapshot = _normalizar_snapshot_json(fila.get('snapshot_json'))

    origen = _coalescer_texto(snapshot.get('origen'), fila.get('carga_origen'))
    destino = _coalescer_texto(snapshot.get('destino'), fila.get('carga_destino'))
    tipo_carga = _coalescer_texto(
        snapshot.get('tipo_carga'),
        fila.get('carga_tipo_carga'),
    )

    valor = _obtener_valor_entero(snapshot.get('valor'))
    if valor == 0:
        valor = _obtener_valor_entero(fila.get('carga_valor'))

    estado = _resolver_estado_viaje(
        snapshot.get('estado'),
        fila.get('carga_activo'),
        fila.get('carga_estado'),
    )

    fecha_publicacion = (
        _parsear_fecha_iso(snapshot.get('fecha_publicacion'))
        or _parsear_fecha_iso(fila.get('carga_created_at'))
    )

    eliminado_por = _coalescer_texto(
        fila.get('eliminado_por_nombre'),
        fila.get('eliminado_por_email'),
        fila.get('eliminado_por'),
    )

    base_data: dict[str, object] = {
        'id': str(fila['id']),
        'carga_id': str(fila['carga_id']),
        'causal_id': int(fila['causal_id']),
        'causal_nombre': _normalizar_nombre_causal(fila.get('causal_nombre')),
        'observacion': str(fila['observacion']) if fila.get('observacion') else None,
        'eliminado_por': eliminado_por,
        'eliminado_en': _normalizar_fecha(fila.get('eliminado_en')),
        'origen': origen,
        'destino': destino,
        'valor': valor,
    }

    if not incluir_snapshot:
        return ViajeEliminadoOut(**base_data)

    return ViajeEliminadoDetalleOut(
        **base_data,
        tipo_carga=tipo_carga,
        estado=estado,
        fecha_publicacion=fecha_publicacion,
        snapshot_json=snapshot or None,
    )


def _obtener_viaje_no_eliminado(
    db: Session,
    viaje_id: UUID,
) -> models.Cargo | None:
    viaje = (
        db.query(models.Cargo)
        .filter(
            models.Cargo.id == viaje_id,
            models.Cargo.estado == 'publicado',
            text(
                """
                NOT EXISTS (
                    SELECT 1
                    FROM conexion_carga.carga_eliminada ce
                    WHERE ce.carga_id = conexion_carga.carga.id
                )
                """
            ),
        )
        .first()
    )
    return viaje


@router.get('/causales-eliminacion', response_model=list[CausalEliminacionOut])
def obtener_causales_eliminacion(
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    _asegurar_tablas_eliminacion(db)

    causales = db.execute(
        text(
            """
            SELECT id, nombre, descripcion
            FROM conexion_carga.causales_eliminacion
            WHERE activo = TRUE
              AND LOWER(TRIM(nombre)) NOT IN (
                    LOWER('Otro (Observación libre)'),
                    LOWER('Otro (Observacion libre)')
              )
            ORDER BY
                CASE
                    WHEN LOWER(TRIM(nombre)) IN (LOWER('Otro'), LOWER('Otra'))
                        THEN 1
                    ELSE 0
                END,
                LOWER(TRIM(nombre)) ASC
            """
        )
    ).mappings().all()

    return [
        CausalEliminacionOut(
            id=int(row['id']),
            nombre=_normalizar_nombre_causal(row['nombre']),
            descripcion=str(row['descripcion']) if row['descripcion'] else None,
        )
        for row in causales
    ]


@router.get('/viajes', response_model=ListaViajesAdminOut)
def obtener_viajes_admin(
    q: str = Query(default='', max_length=255),
    estado: FiltroEstadoViajeAdmin = Query(
        default='todos',
        pattern='^(activo|inactivo|todos)$',
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    _asegurar_tablas_eliminacion(db)
    _sincronizar_vigencia_publicaciones(db)

    termino = (q or '').strip()
    filtro_like = f'%{termino}%'
    offset = (page - 1) * page_size

    query = db.query(models.Cargo).filter(
        models.Cargo.estado == 'publicado',
        text(
            """
            NOT EXISTS (
                SELECT 1
                FROM conexion_carga.carga_eliminada ce
                WHERE ce.carga_id = conexion_carga.carga.id
            )
            """
        ),
    )

    if estado == 'activo':
        query = query.filter(models.Cargo.activo.is_(True))
    elif estado == 'inactivo':
        query = query.filter(models.Cargo.activo.is_(False))

    if termino:
        query = query.filter(
            or_(
                cast(models.Cargo.id, String).ilike(filtro_like),
                models.Cargo.origen.ilike(filtro_like),
                models.Cargo.destino.ilike(filtro_like),
                models.Cargo.tipo_carga.ilike(filtro_like),
                models.Cargo.comercial.ilike(filtro_like),
                models.Cargo.contacto.ilike(filtro_like),
                models.Cargo.conductor.ilike(filtro_like),
                models.Cargo.tipo_vehiculo.ilike(filtro_like),
                cast(models.Cargo.valor, String).ilike(filtro_like),
            )
        )

    total = int(query.count() or 0)
    viajes = (
        query.order_by(models.Cargo.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return ListaViajesAdminOut(
        total=total,
        page=page,
        page_size=page_size,
        items=[_serializar_viaje(viaje) for viaje in viajes],
    )


@router.get('/viajes/sugerencias/empresas', response_model=list[str])
def obtener_sugerencias_empresas_viajes_admin(
    q: str = Query(default='', max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    termino = ' '.join(str(q or '').split())

    filas = db.execute(
        text(
            """
            WITH empresas_normalizadas AS (
                SELECT
                    MIN(REGEXP_REPLACE(TRIM(company_name), '\\s+', ' ', 'g')) AS nombre
                FROM conexion_carga.users
                WHERE NULLIF(TRIM(company_name), '') IS NOT NULL
                  AND (
                        :termino = ''
                        OR REGEXP_REPLACE(TRIM(company_name), '\\s+', ' ', 'g') ILIKE :termino_like
                  )
                GROUP BY LOWER(REGEXP_REPLACE(TRIM(company_name), '\\s+', ' ', 'g'))
            )
            SELECT nombre
            FROM empresas_normalizadas
            ORDER BY LOWER(nombre) ASC
            LIMIT :limit
            """
        ),
        {
            'termino': termino,
            'termino_like': f'%{termino}%',
            'limit': limit,
        },
    ).scalars().all()

    return [str(nombre).strip() for nombre in filas if str(nombre or '').strip()]


@router.get('/viajes/exportacion', response_model=list[ViajeAdminExportOut])
def exportar_viajes_admin(
    q: str = Query(default='', max_length=255),
    estado: FiltroEstadoViajeAdmin = Query(
        default='todos',
        pattern='^(activo|inactivo|todos)$',
    ),
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    _asegurar_tablas_eliminacion(db)
    _sincronizar_vigencia_publicaciones(db)

    termino = (q or '').strip()
    filtro_like = f'%{termino}%'

    query = db.query(models.Cargo).filter(
        models.Cargo.estado == 'publicado',
        text(
            """
            NOT EXISTS (
                SELECT 1
                FROM conexion_carga.carga_eliminada ce
                WHERE ce.carga_id = conexion_carga.carga.id
            )
            """
        ),
    )

    if estado == 'activo':
        query = query.filter(models.Cargo.activo.is_(True))
    elif estado == 'inactivo':
        query = query.filter(models.Cargo.activo.is_(False))

    if termino:
        query = query.filter(
            or_(
                cast(models.Cargo.id, String).ilike(filtro_like),
                models.Cargo.origen.ilike(filtro_like),
                models.Cargo.destino.ilike(filtro_like),
                models.Cargo.tipo_carga.ilike(filtro_like),
                models.Cargo.comercial.ilike(filtro_like),
                models.Cargo.contacto.ilike(filtro_like),
                models.Cargo.conductor.ilike(filtro_like),
                models.Cargo.tipo_vehiculo.ilike(filtro_like),
                cast(models.Cargo.valor, String).ilike(filtro_like),
            )
        )

    viajes = query.order_by(models.Cargo.created_at.desc()).all()

    usuarios_por_id = {
        str(row.id): row
        for row in db.query(
            models.User.id,
            models.User.first_name,
            models.User.last_name,
            models.User.email,
            models.User.company_name,
        )
        .filter(models.User.id.in_([viaje.comercial_id for viaje in viajes if viaje.comercial_id]))
        .all()
    }

    resultados: list[ViajeAdminExportOut] = []
    for viaje in viajes:
        publicador = usuarios_por_id.get(str(viaje.comercial_id))
        usuario = _resolver_usuario_publicador(
            viaje.comercial,
            (
                ' '.join(
                    parte
                    for parte in [
                        str(publicador.first_name or '').strip()
                        if publicador
                        else '',
                        str(publicador.last_name or '').strip()
                        if publicador
                        else '',
                    ]
                    if parte
                )
                if publicador
                else None
            ),
            publicador.email if publicador else None,
        )
        empresa = _resolver_empresa_publicadora(
            viaje.empresa,
            publicador.company_name if publicador else None,
        )

        resultados.append(
            ViajeAdminExportOut(
                id_viaje=str(viaje.id),
                usuario=usuario,
                empresa=empresa,
                origen=viaje.origen,
                destino=viaje.destino,
                estado='Activo' if bool(viaje.activo) else 'Inactivo',
                tipo_carga=viaje.tipo_carga,
                valor=_obtener_valor_entero(viaje.valor),
                fecha_creacion=viaje.created_at,
            )
        )

    return resultados


@router.get('/viajes/{viaje_id}', response_model=ViajeAdminOut)
def obtener_detalle_viaje_admin(
    viaje_id: UUID,
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    _asegurar_tablas_eliminacion(db)
    _sincronizar_vigencia_publicaciones(db)

    viaje = _obtener_viaje_no_eliminado(db=db, viaje_id=viaje_id)
    if not viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Viaje no encontrado o ya eliminado.',
        )

    return _serializar_viaje(viaje)


@router.post(
    '/viajes',
    response_model=ViajeAdminOut,
    status_code=status.HTTP_201_CREATED,
)
def crear_viaje_admin(
    payload: schemas.CargoCreate,
    db: Session = Depends(get_db),
    current: models.User = Depends(_asegurar_usuario_admin),
):
    _sincronizar_vigencia_publicaciones(db)

    try:
        viaje = crud.create_cargo(db, payload, current)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No fue posible crear el viaje con los datos enviados.',
        )

    return _serializar_viaje(viaje)


@router.patch('/viajes/{viaje_id}', response_model=ViajeAdminOut)
def actualizar_viaje_admin(
    viaje_id: UUID,
    payload: ActualizarViajeAdminIn,
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    _asegurar_tablas_eliminacion(db)
    _sincronizar_vigencia_publicaciones(db)

    viaje = _obtener_viaje_no_eliminado(db=db, viaje_id=viaje_id)
    if not viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Viaje no encontrado o ya eliminado.',
        )

    cambios = payload.model_dump(exclude_unset=True)
    if not cambios:
        return _serializar_viaje(viaje)

    campos_requeridos = {'origen', 'destino', 'tipo_carga'}
    for campo in campos_requeridos:
        if campo in cambios and not str(cambios[campo] or '').strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f'El campo "{campo}" es obligatorio.',
            )

    for campo in (
        'empresa_id',
        'origen',
        'destino',
        'tipo_carga',
        'peso',
        'valor',
        'comercial',
        'contacto',
        'observaciones',
        'conductor',
        'tipo_vehiculo',
        'premium_trip',
    ):
        if campo in cambios:
            setattr(viaje, campo, cambios[campo])

    if 'duration_hours' in cambios and cambios['duration_hours'] is not None:
        viaje.duracion_publicacion = timedelta(hours=int(cambios['duration_hours']))

    try:
        db.add(viaje)
        db.commit()
        db.refresh(viaje)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No fue posible actualizar el viaje con los datos enviados.',
        )

    return _serializar_viaje(viaje)


@router.post('/viajes/{viaje_id}/eliminar', response_model=EliminarViajeAdminOut)
def eliminar_viaje_admin(
    viaje_id: UUID,
    payload: EliminarViajeAdminIn,
    db: Session = Depends(get_db),
    current: models.User = Depends(_asegurar_usuario_admin),
):
    _asegurar_tablas_eliminacion(db)

    viaje = _obtener_viaje_no_eliminado(db=db, viaje_id=viaje_id)
    if not viaje:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Viaje no encontrado o ya eliminado.',
        )

    causal = db.execute(
        text(
            """
            SELECT id, nombre, activo
            FROM conexion_carga.causales_eliminacion
            WHERE id = :causal_id
            LIMIT 1
            """
        ),
        {'causal_id': payload.causal_id},
    ).mappings().first()

    if not causal or not bool(causal['activo']):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='La causal seleccionada no existe o se encuentra inactiva.',
        )

    observacion = (payload.observacion or '').strip()
    causal_nombre = str(causal['nombre'] or '').strip()
    causal_es_otro = _es_causal_observacion_libre(causal_nombre)

    if causal_es_otro and len(observacion) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='La observación es obligatoria.',
        )

    if causal_es_otro and len(observacion) < MINIMO_OBSERVACION_OTRO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f'La observación debe tener mínimo {MINIMO_OBSERVACION_OTRO} caracteres.'
            ),
        )

    if observacion and len(observacion) > MAXIMO_OBSERVACION:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f'La observación no debe superar {MAXIMO_OBSERVACION} caracteres.'
            ),
        )

    snapshot_json = json.dumps(_snapshot_viaje(viaje))

    try:
        eliminado_id = db.execute(
            text(
                """
                INSERT INTO conexion_carga.carga_eliminada (
                    carga_id,
                    causal_id,
                    observacion,
                    eliminado_por,
                    eliminado_en,
                    snapshot_json
                )
                VALUES (
                    CAST(:carga_id AS uuid),
                    :causal_id,
                    :observacion,
                    CAST(:eliminado_por AS uuid),
                    NOW(),
                    CAST(:snapshot_json AS jsonb)
                )
                RETURNING id
                """
            ),
            {
                'carga_id': str(viaje.id),
                'causal_id': int(payload.causal_id),
                'observacion': observacion or None,
                'eliminado_por': str(current.id),
                'snapshot_json': snapshot_json,
            },
        ).scalar()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='El viaje ya fue eliminado previamente.',
        )

    return EliminarViajeAdminOut(
        ok=True,
        message='Viaje eliminado correctamente con trazabilidad administrativa.',
        carga_eliminada_id=str(eliminado_id),
    )


@router.get('/viajes-eliminados', response_model=ListaViajesEliminadosOut)
def obtener_viajes_eliminados_admin(
    q: str = Query(default='', max_length=255),
    causal_id: int | None = Query(default=None, ge=1),
    fecha_desde: str | None = Query(default=None),
    fecha_hasta: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    _asegurar_tablas_eliminacion(db)

    termino = (q or '').strip()
    fecha_desde_dt = _parsear_fecha_filtro(
        fecha_desde,
        nombre_parametro='fecha_desde',
        fin_de_dia=False,
    )
    fecha_hasta_dt = _parsear_fecha_filtro(
        fecha_hasta,
        nombre_parametro='fecha_hasta',
        fin_de_dia=True,
    )

    if fecha_desde_dt and fecha_hasta_dt and fecha_desde_dt > fecha_hasta_dt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='El rango de fechas no es válido: fecha_desde no puede ser mayor a fecha_hasta.',
        )

    params: dict[str, object] = {
        'limit': page_size,
        'offset': (page - 1) * page_size,
    }

    filtros_sql: list[str] = []
    if termino:
        filtros_sql.append(
            """
            (
                COALESCE(ce.observacion, '') ILIKE :q_like
                OR COALESCE(ca.nombre, '') ILIKE :q_like
                OR COALESCE(NULLIF(ce.snapshot_json->>'origen', ''), COALESCE(c.origen, '')) ILIKE :q_like
                OR COALESCE(NULLIF(ce.snapshot_json->>'destino', ''), COALESCE(c.destino, '')) ILIKE :q_like
                OR CAST(ce.carga_id AS TEXT) ILIKE :q_like
            )
            """
        )
        params['q_like'] = f'%{termino}%'

    if causal_id is not None:
        filtros_sql.append('ce.causal_id = :causal_id')
        params['causal_id'] = causal_id

    if fecha_desde_dt:
        filtros_sql.append('ce.eliminado_en >= :fecha_desde')
        params['fecha_desde'] = fecha_desde_dt

    if fecha_hasta_dt:
        filtros_sql.append('ce.eliminado_en <= :fecha_hasta')
        params['fecha_hasta'] = fecha_hasta_dt

    where_clause = f"WHERE {' AND '.join(filtros_sql)}" if filtros_sql else ''
    from_clause = """
        FROM conexion_carga.carga_eliminada ce
        JOIN conexion_carga.causales_eliminacion ca
          ON ca.id = ce.causal_id
        LEFT JOIN conexion_carga.carga c
          ON c.id = ce.carga_id
        LEFT JOIN conexion_carga.users u
          ON u.id = ce.eliminado_por
    """

    total = db.execute(
        text(
            f"""
            SELECT COUNT(*)
            {from_clause}
            {where_clause}
            """
        ),
        params,
    ).scalar()

    filas = db.execute(
        text(
            f"""
            SELECT
                ce.id,
                ce.carga_id,
                ce.causal_id,
                ce.observacion,
                ce.eliminado_por,
                ce.eliminado_en,
                ce.snapshot_json,
                ca.nombre AS causal_nombre,
                u.email AS eliminado_por_email,
                NULLIF(CONCAT_WS(' ', u.first_name, u.last_name), '') AS eliminado_por_nombre,
                c.origen AS carga_origen,
                c.destino AS carga_destino,
                c.valor AS carga_valor,
                c.tipo_carga AS carga_tipo_carga,
                c.activo AS carga_activo,
                c.estado AS carga_estado,
                c.created_at AS carga_created_at
            {from_clause}
            {where_clause}
            ORDER BY ce.eliminado_en DESC
            OFFSET :offset
            LIMIT :limit
            """
        ),
        params,
    ).mappings().all()

    items = [
        _serializar_viaje_eliminado_desde_fila(fila, incluir_snapshot=False)
        for fila in filas
    ]

    return ListaViajesEliminadosOut(
        total=int(total or 0),
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get(
    '/viajes-eliminados/exportacion',
    response_model=list[ViajeEliminadoAdminExportOut],
)
def exportar_viajes_eliminados_admin(
    q: str = Query(default='', max_length=255),
    causal_id: int | None = Query(default=None, ge=1),
    fecha_desde: str | None = Query(default=None),
    fecha_hasta: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    _asegurar_tablas_eliminacion(db)

    termino = (q or '').strip()
    fecha_desde_dt = _parsear_fecha_filtro(
        fecha_desde,
        nombre_parametro='fecha_desde',
        fin_de_dia=False,
    )
    fecha_hasta_dt = _parsear_fecha_filtro(
        fecha_hasta,
        nombre_parametro='fecha_hasta',
        fin_de_dia=True,
    )

    if fecha_desde_dt and fecha_hasta_dt and fecha_desde_dt > fecha_hasta_dt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='El rango de fechas no es válido: fecha_desde no puede ser mayor a fecha_hasta.',
        )

    params: dict[str, object] = {}
    filtros_sql: list[str] = []

    if termino:
        filtros_sql.append(
            """
            (
                COALESCE(ce.observacion, '') ILIKE :q_like
                OR COALESCE(ca.nombre, '') ILIKE :q_like
                OR COALESCE(NULLIF(ce.snapshot_json->>'origen', ''), COALESCE(c.origen, '')) ILIKE :q_like
                OR COALESCE(NULLIF(ce.snapshot_json->>'destino', ''), COALESCE(c.destino, '')) ILIKE :q_like
                OR CAST(ce.carga_id AS TEXT) ILIKE :q_like
            )
            """
        )
        params['q_like'] = f'%{termino}%'

    if causal_id is not None:
        filtros_sql.append('ce.causal_id = :causal_id')
        params['causal_id'] = causal_id

    if fecha_desde_dt:
        filtros_sql.append('ce.eliminado_en >= :fecha_desde')
        params['fecha_desde'] = fecha_desde_dt

    if fecha_hasta_dt:
        filtros_sql.append('ce.eliminado_en <= :fecha_hasta')
        params['fecha_hasta'] = fecha_hasta_dt

    where_clause = f"WHERE {' AND '.join(filtros_sql)}" if filtros_sql else ''
    from_clause = """
        FROM conexion_carga.carga_eliminada ce
        JOIN conexion_carga.causales_eliminacion ca
          ON ca.id = ce.causal_id
        LEFT JOIN conexion_carga.carga c
          ON c.id = ce.carga_id
        LEFT JOIN conexion_carga.users eliminador
          ON eliminador.id = ce.eliminado_por
        LEFT JOIN conexion_carga.users publicador
          ON publicador.id = c.comercial_id
    """

    filas = db.execute(
        text(
            f"""
            SELECT
                ce.id,
                ce.carga_id,
                ce.causal_id,
                ce.observacion,
                ce.eliminado_por,
                ce.eliminado_en,
                ce.snapshot_json,
                ca.nombre AS causal_nombre,
                eliminador.email AS eliminado_por_email,
                NULLIF(CONCAT_WS(' ', eliminador.first_name, eliminador.last_name), '') AS eliminado_por_nombre,
                c.origen AS carga_origen,
                c.destino AS carga_destino,
                c.valor AS carga_valor,
                c.tipo_carga AS carga_tipo_carga,
                c.activo AS carga_activo,
                c.estado AS carga_estado,
                c.created_at AS carga_created_at,
                c.comercial AS carga_comercial,
                c.empresa AS carga_empresa,
                NULLIF(CONCAT_WS(' ', publicador.first_name, publicador.last_name), '') AS publicador_nombre,
                publicador.email AS publicador_email,
                publicador.company_name AS publicador_empresa
            {from_clause}
            {where_clause}
            ORDER BY ce.eliminado_en DESC
            """
        ),
        params,
    ).mappings().all()

    resultados: list[ViajeEliminadoAdminExportOut] = []
    for fila in filas:
        snapshot = _normalizar_snapshot_json(fila.get('snapshot_json'))
        usuario = _resolver_usuario_publicador(
            snapshot.get('comercial'),
            fila.get('carga_comercial'),
            fila.get('publicador_nombre'),
            fila.get('publicador_email'),
        )
        empresa = _resolver_empresa_publicadora(
            snapshot.get('empresa'),
            fila.get('carga_empresa'),
            fila.get('publicador_empresa'),
        )
        fecha_creacion = _parsear_fecha_iso(snapshot.get('created_at'))
        if fecha_creacion is None:
            fecha_creacion = _parsear_fecha_iso(fila.get('carga_created_at'))

        resultados.append(
            ViajeEliminadoAdminExportOut(
                id_viaje=str(fila['carga_id']),
                usuario=usuario,
                empresa=empresa,
                origen=_coalescer_texto(snapshot.get('origen'), fila.get('carga_origen')),
                destino=_coalescer_texto(
                    snapshot.get('destino'),
                    fila.get('carga_destino'),
                ),
                causal_eliminacion=_normalizar_nombre_causal(
                    str(fila['causal_nombre'] or '')
                ),
                observacion=_coalescer_texto(fila.get('observacion')),
                fecha_creacion_viaje=fecha_creacion,
                fecha_eliminacion=_normalizar_fecha(fila['eliminado_en']),
            )
        )

    return resultados


@router.get('/viajes-eliminados/{registro_id}', response_model=ViajeEliminadoDetalleOut)
def obtener_detalle_viaje_eliminado_admin(
    registro_id: UUID,
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    _asegurar_tablas_eliminacion(db)

    fila = db.execute(
        text(
            """
            SELECT
                ce.id,
                ce.carga_id,
                ce.causal_id,
                ce.observacion,
                ce.eliminado_por,
                ce.eliminado_en,
                ce.snapshot_json,
                ca.nombre AS causal_nombre,
                u.email AS eliminado_por_email,
                NULLIF(CONCAT_WS(' ', u.first_name, u.last_name), '') AS eliminado_por_nombre,
                c.origen AS carga_origen,
                c.destino AS carga_destino,
                c.valor AS carga_valor,
                c.tipo_carga AS carga_tipo_carga,
                c.activo AS carga_activo,
                c.estado AS carga_estado,
                c.created_at AS carga_created_at
            FROM conexion_carga.carga_eliminada ce
            JOIN conexion_carga.causales_eliminacion ca
              ON ca.id = ce.causal_id
            LEFT JOIN conexion_carga.carga c
              ON c.id = ce.carga_id
            LEFT JOIN conexion_carga.users u
              ON u.id = ce.eliminado_por
            WHERE ce.id = CAST(:registro_id AS uuid)
            LIMIT 1
            """
        ),
        {'registro_id': str(registro_id)},
    ).mappings().first()

    if not fila:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Registro de viaje eliminado no encontrado.',
        )

    return _serializar_viaje_eliminado_desde_fila(
        fila,
        incluir_snapshot=True,
    )
