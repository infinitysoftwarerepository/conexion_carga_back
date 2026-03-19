from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models
from app.db import get_db
from app.routers.dashboard_admin import _asegurar_usuario_admin
from app.schemas_puntos_admin import (
    ActualizarPuntosAdminIn,
    ActualizarPuntosAdminOut,
    ListaUsuariosPuntosAdminOut,
    ListaReferidosAdminOut,
    QuitarReferidoAdminOut,
    UsuarioPuntosAdminOut,
    UsuarioReferidoAdminOut,
)

router = APIRouter(prefix='/api/admin/puntos', tags=['Admin Puntos'])


def _normalizar_texto(valor: object) -> str | None:
    if valor is None:
        return None

    texto = str(valor).strip()
    return texto or None


def _obtener_entero(valor: object) -> int:
    if valor is None:
        return 0

    try:
        return int(Decimal(valor))
    except Exception:
        return 0


def _serializar_usuario_puntos(row) -> UsuarioPuntosAdminOut:
    return UsuarioPuntosAdminOut(
        id=str(row['id']),
        email=str(row['email']),
        first_name=str(row['first_name']),
        last_name=str(row['last_name']),
        phone=_normalizar_texto(row.get('phone')),
        company_name=_normalizar_texto(row.get('company_name')),
        active=bool(row.get('active')),
        created_at=row['created_at'],
        points=_obtener_entero(row.get('points')),
        referred_count=_obtener_entero(row.get('referred_count')),
    )


def _serializar_usuario_referido(row) -> UsuarioReferidoAdminOut:
    return UsuarioReferidoAdminOut(
        id=str(row['id']),
        email=str(row['email']),
        first_name=str(row['first_name']),
        last_name=str(row['last_name']),
        phone=_normalizar_texto(row.get('phone')),
        company_name=_normalizar_texto(row.get('company_name')),
        active=bool(row.get('active')),
        created_at=row['created_at'],
    )


def _obtener_usuario_por_id(db: Session, user_id: UUID | str):
    return db.execute(
        text(
            """
            SELECT
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.phone,
                u.company_name,
                u.active,
                u.created_at,
                u.points,
                COALESCE(refs.referred_count, 0) AS referred_count
            FROM conexion_carga.users u
            LEFT JOIN (
                SELECT
                    referred_by_id,
                    COUNT(*) AS referred_count
                FROM conexion_carga.users
                WHERE referred_by_id IS NOT NULL
                GROUP BY referred_by_id
            ) refs
                ON refs.referred_by_id = u.id
            WHERE u.id = CAST(:user_id AS uuid)
            LIMIT 1
            """
        ),
        {'user_id': str(user_id)},
    ).mappings().first()


def _tabla_auditoria_existe(db: Session) -> bool:
    return bool(
        db.execute(
            text(
                """
                SELECT to_regclass('conexion_carga.auditoria_puntos_referidos') IS NOT NULL
                """
            )
        ).scalar()
    )


def _registrar_auditoria_puntos(
    db: Session,
    *,
    user_id: UUID | str,
    admin_user_id: UUID | str | None,
    accion: str,
    puntos_anteriores: int,
    puntos_nuevos: int,
    detalle: str | None,
) -> None:
    if not _tabla_auditoria_existe(db):
        return

    db.execute(
        text(
            """
            INSERT INTO conexion_carga.auditoria_puntos_referidos (
                user_id,
                admin_user_id,
                accion,
                puntos_anteriores,
                puntos_nuevos,
                detalle
            )
            VALUES (
                CAST(:user_id AS uuid),
                CAST(:admin_user_id AS uuid),
                :accion,
                :puntos_anteriores,
                :puntos_nuevos,
                :detalle
            )
            """
        ),
        {
            'user_id': str(user_id),
            'admin_user_id': str(admin_user_id) if admin_user_id else None,
            'accion': accion,
            'puntos_anteriores': puntos_anteriores,
            'puntos_nuevos': puntos_nuevos,
            'detalle': detalle,
        },
    )


@router.get('', response_model=ListaUsuariosPuntosAdminOut)
def obtener_ranking_puntos(
    q: str = Query(default='', max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    termino = (q or '').strip()

    filtros: list[str] = []
    params: dict[str, object] = {
        'limit': page_size,
        'offset': (page - 1) * page_size,
    }

    if termino:
        filtros.append(
            """
            (
                COALESCE(u.email, '') ILIKE :q_like
                OR COALESCE(u.first_name, '') ILIKE :q_like
                OR COALESCE(u.last_name, '') ILIKE :q_like
                OR COALESCE(u.phone, '') ILIKE :q_like
                OR COALESCE(u.company_name, '') ILIKE :q_like
                OR COALESCE(u.first_name || ' ' || u.last_name, '') ILIKE :q_like
            )
            """
        )
        params['q_like'] = f'%{termino}%'

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ''

    total = db.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM conexion_carga.users u
            {where_clause}
            """
        ),
        params,
    ).scalar()

    filas = db.execute(
        text(
            f"""
            SELECT
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.phone,
                u.company_name,
                u.active,
                u.created_at,
                u.points,
                COALESCE(refs.referred_count, 0) AS referred_count
            FROM conexion_carga.users u
            LEFT JOIN (
                SELECT
                    referred_by_id,
                    COUNT(*) AS referred_count
                FROM conexion_carga.users
                WHERE referred_by_id IS NOT NULL
                GROUP BY referred_by_id
            ) refs
                ON refs.referred_by_id = u.id
            {where_clause}
            ORDER BY COALESCE(u.points, 0) DESC, u.created_at ASC, LOWER(u.email) ASC
            OFFSET :offset
            LIMIT :limit
            """
        ),
        params,
    ).mappings().all()

    return ListaUsuariosPuntosAdminOut(
        total=int(total or 0),
        page=page,
        page_size=page_size,
        items=[_serializar_usuario_puntos(fila) for fila in filas],
    )


@router.get('/{user_id}/referidos', response_model=ListaReferidosAdminOut)
def obtener_referidos_usuario(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    fila_padre = _obtener_usuario_por_id(db=db, user_id=user_id)
    if not fila_padre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuario no encontrado.',
        )

    filas = db.execute(
        text(
            """
            SELECT
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.phone,
                u.company_name,
                u.active,
                u.created_at
            FROM conexion_carga.users u
            WHERE u.referred_by_id = CAST(:user_id AS uuid)
            ORDER BY u.created_at ASC, LOWER(u.email) ASC
            """
        ),
        {'user_id': str(user_id)},
    ).mappings().all()

    return ListaReferidosAdminOut(
        total=len(filas),
        items=[_serializar_usuario_referido(fila) for fila in filas],
    )


@router.patch('/{user_id}', response_model=ActualizarPuntosAdminOut)
def actualizar_puntos_usuario(
    user_id: UUID,
    payload: ActualizarPuntosAdminIn,
    db: Session = Depends(get_db),
    current: models.User = Depends(_asegurar_usuario_admin),
):
    fila_actual = _obtener_usuario_por_id(db=db, user_id=user_id)
    if not fila_actual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuario no encontrado.',
        )

    puntos_anteriores = _obtener_entero(fila_actual.get('points'))
    puntos_nuevos = int(payload.points)

    db.execute(
        text(
            """
            UPDATE conexion_carga.users
            SET points = :points
            WHERE id = CAST(:user_id AS uuid)
            """
        ),
        {
            'user_id': str(user_id),
            'points': puntos_nuevos,
        },
    )

    _registrar_auditoria_puntos(
        db,
        user_id=user_id,
        admin_user_id=current.id,
        accion='actualizacion_manual',
        puntos_anteriores=puntos_anteriores,
        puntos_nuevos=puntos_nuevos,
        detalle='Actualización manual de puntos desde el panel administrativo.',
    )

    db.commit()

    fila_actualizada = _obtener_usuario_por_id(db=db, user_id=user_id)
    if not fila_actualizada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuario no encontrado después de actualizar.',
        )

    return ActualizarPuntosAdminOut(
        ok=True,
        message='Puntos actualizados correctamente.',
        user=_serializar_usuario_puntos(fila_actualizada),
    )


@router.post('/{user_id}/quitar', response_model=ActualizarPuntosAdminOut)
def quitar_usuario_del_ranking(
    user_id: UUID,
    db: Session = Depends(get_db),
    current: models.User = Depends(_asegurar_usuario_admin),
):
    fila_actual = _obtener_usuario_por_id(db=db, user_id=user_id)
    if not fila_actual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuario no encontrado.',
        )

    puntos_anteriores = _obtener_entero(fila_actual.get('points'))

    db.execute(
        text(
            """
            UPDATE conexion_carga.users
            SET points = 0
            WHERE id = CAST(:user_id AS uuid)
            """
        ),
        {'user_id': str(user_id)},
    )

    _registrar_auditoria_puntos(
        db,
        user_id=user_id,
        admin_user_id=current.id,
        accion='quitar_del_ranking',
        puntos_anteriores=puntos_anteriores,
        puntos_nuevos=0,
        detalle='Reinicio de puntos a cero desde el panel administrativo.',
    )

    db.commit()

    fila_actualizada = _obtener_usuario_por_id(db=db, user_id=user_id)
    if not fila_actualizada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuario no encontrado después de actualizar.',
        )

    return ActualizarPuntosAdminOut(
        ok=True,
        message='Los puntos del usuario se reiniciaron a 0 correctamente.',
        user=_serializar_usuario_puntos(fila_actualizada),
    )


@router.post(
    '/{user_id}/referidos/{referred_user_id}/quitar',
    response_model=QuitarReferidoAdminOut,
)
def quitar_referido_usuario(
    user_id: UUID,
    referred_user_id: UUID,
    db: Session = Depends(get_db),
    current: models.User = Depends(_asegurar_usuario_admin),
):
    fila_padre = _obtener_usuario_por_id(db=db, user_id=user_id)
    if not fila_padre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuario principal no encontrado.',
        )

    fila_referido = db.execute(
        text(
            """
            SELECT
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.referred_by_id
            FROM conexion_carga.users u
            WHERE u.id = CAST(:referred_user_id AS uuid)
            LIMIT 1
            """
        ),
        {'referred_user_id': str(referred_user_id)},
    ).mappings().first()

    if not fila_referido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuario referido no encontrado.',
        )

    referido_por_id = fila_referido.get('referred_by_id')
    if not referido_por_id or str(referido_por_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='El referido no está asociado al usuario seleccionado.',
        )

    puntos_anteriores = _obtener_entero(fila_padre.get('points'))
    puntos_nuevos = max(puntos_anteriores - 1, 0)
    detalle = (
        'Se retiró el referido '
        f"{fila_referido.get('email') or referred_user_id} "
        'desde el panel administrativo.'
    )

    try:
        resultado_retiro = db.execute(
            text(
                """
                UPDATE conexion_carga.users
                SET referred_by_id = NULL
                WHERE id = CAST(:referred_user_id AS uuid)
                  AND referred_by_id = CAST(:user_id AS uuid)
                """
            ),
            {
                'referred_user_id': str(referred_user_id),
                'user_id': str(user_id),
            },
        )

        if (resultado_retiro.rowcount or 0) <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='La relación del referido cambió antes de completar la operación.',
            )

        db.execute(
            text(
                """
                UPDATE conexion_carga.users
                SET points = :points
                WHERE id = CAST(:user_id AS uuid)
                """
            ),
            {
                'user_id': str(user_id),
                'points': puntos_nuevos,
            },
        )

        _registrar_auditoria_puntos(
            db,
            user_id=user_id,
            admin_user_id=current.id,
            accion='quitar_referido',
            puntos_anteriores=puntos_anteriores,
            puntos_nuevos=puntos_nuevos,
            detalle=detalle,
        )

        db.commit()
    except Exception:
        db.rollback()
        raise

    fila_padre_actualizada = _obtener_usuario_por_id(db=db, user_id=user_id)
    if not fila_padre_actualizada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuario principal no encontrado después de actualizar.',
        )

    return QuitarReferidoAdminOut(
        ok=True,
        message='El referido se retiró correctamente y los puntos del usuario fueron ajustados.',
        parent_user=_serializar_usuario_puntos(fila_padre_actualizada),
        removed_referred_id=str(referred_user_id),
    )
