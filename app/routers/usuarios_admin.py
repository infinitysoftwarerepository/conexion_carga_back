from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.db import get_db
from app.routers.dashboard_admin import _asegurar_usuario_admin
from app.schemas_exportacion_admin import UsuarioAdminExportOut
from app.schemas_usuarios_admin import (
    ActualizarUsuarioAdminIn,
    CambiarEstadoUsuarioAdminIn,
    CambiarEstadoUsuarioAdminOut,
    CrearUsuarioAdminIn,
    EstadoFiltroUsuarioAdmin,
    ListaUsuariosAdminOut,
    TipoFiltroUsuarioAdmin,
    UsuarioAdminOut,
)
from app.security import get_password_hash

router = APIRouter(prefix='/api/admin/usuarios', tags=['Admin Usuarios'])
ROL_ADMINISTRADOR_NOMBRE = 'Administrador'


def _normalizar_texto(valor: object) -> str | None:
    if valor is None:
        return None

    texto = str(valor).strip()
    return texto or None


def _normalizar_email(email: object) -> str:
    return str(email or '').strip().lower()


def _obtener_entero(valor: object) -> int:
    if valor is None:
        return 0

    try:
        return int(Decimal(valor))
    except Exception:
        return 0


def _obtener_rol_admin_id(db: Session) -> int:
    rol_id = db.execute(
        text(
            """
            SELECT id
            FROM conexion_carga.rol
            WHERE LOWER(nombre) = LOWER(:nombre)
            ORDER BY id ASC
            LIMIT 1
            """
        ),
        {'nombre': ROL_ADMINISTRADOR_NOMBRE},
    ).scalar()

    if rol_id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='No fue posible resolver el rol Administrador.',
        )

    return int(rol_id)


def _obtener_usuario_por_id(db: Session, usuario_id: UUID | str):
    return db.execute(
        text(
            """
            SELECT
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.phone,
                u.is_company,
                u.company_name,
                u.active,
                u.created_at,
                u.points,
                u.is_premium,
                u.is_driver,
                u.rol_id,
                r.nombre AS rol_nombre,
                u.referred_by_id,
                ref.email AS referred_by_email
            FROM conexion_carga.users u
            LEFT JOIN conexion_carga.rol r
              ON r.id = u.rol_id
            LEFT JOIN conexion_carga.users ref
              ON ref.id = u.referred_by_id
            WHERE u.id = CAST(:usuario_id AS uuid)
            LIMIT 1
            """
        ),
        {'usuario_id': str(usuario_id)},
    ).mappings().first()


def _serializar_usuario(row) -> UsuarioAdminOut:
    return UsuarioAdminOut(
        id=str(row['id']),
        email=str(row['email']),
        first_name=str(row['first_name']),
        last_name=str(row['last_name']),
        phone=_normalizar_texto(row.get('phone')),
        is_company=bool(row.get('is_company')),
        company_name=_normalizar_texto(row.get('company_name')),
        active=bool(row.get('active')),
        created_at=row['created_at'],
        points=_obtener_entero(row.get('points')),
        is_premium=bool(row.get('is_premium')),
        is_driver=bool(row.get('is_driver')),
        rol_id=_obtener_entero(row.get('rol_id')) or None,
        is_admin=str(row.get('rol_nombre') or '').strip().lower()
        == ROL_ADMINISTRADOR_NOMBRE.lower(),
        referred_by_id=str(row['referred_by_id']) if row.get('referred_by_id') else None,
        referred_by_email=_normalizar_texto(row.get('referred_by_email')),
    )


def _obtener_tipo_usuario_exportacion(row: dict[str, object]) -> str:
    tipos: list[str] = []

    if bool(row.get('is_company')):
        tipos.append('Empresa')
    if bool(row.get('is_driver')):
        tipos.append('Conductor')
    if bool(row.get('is_premium')):
        tipos.append('Premium')

    if not tipos:
        tipos.append('Usuario')

    return ', '.join(tipos)


def _construir_consulta_usuarios_admin(
    *,
    q: str,
    estado: EstadoFiltroUsuarioAdmin,
    tipo: TipoFiltroUsuarioAdmin,
    fecha_desde: date | None,
    fecha_hasta: date | None,
) -> tuple[str, str, dict[str, object]]:
    termino = (q or '').strip()

    filtros: list[str] = []
    params: dict[str, object] = {}

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

    if estado == 'habilitado':
        filtros.append('u.active = TRUE')
    elif estado == 'inhabilitado':
        filtros.append('u.active = FALSE')

    if tipo == 'empresa':
        filtros.append('u.is_company = TRUE')
    elif tipo == 'conductor':
        filtros.append('u.is_driver = TRUE')
    elif tipo == 'premium':
        filtros.append('u.is_premium = TRUE')
    elif tipo == 'usuario':
        filtros.append(
            """
            u.is_company = FALSE
            AND u.is_driver = FALSE
            AND u.is_premium = FALSE
            """
        )

    if fecha_desde:
        filtros.append('u.created_at >= CAST(:fecha_desde AS date)')
        params['fecha_desde'] = fecha_desde

    if fecha_hasta:
        filtros.append("u.created_at < CAST(:fecha_hasta AS date) + INTERVAL '1 day'")
        params['fecha_hasta'] = fecha_hasta

    where_clause = f"WHERE {' AND '.join(filtros)}" if filtros else ''
    from_clause = """
        FROM conexion_carga.users u
        LEFT JOIN conexion_carga.rol r
          ON r.id = u.rol_id
        LEFT JOIN conexion_carga.users ref
          ON ref.id = u.referred_by_id
    """

    return from_clause, where_clause, params


@router.get('', response_model=ListaUsuariosAdminOut)
def obtener_usuarios_admin(
    q: str = Query(default='', max_length=255),
    estado: EstadoFiltroUsuarioAdmin = Query(
        default='todos',
        pattern='^(todos|habilitado|inhabilitado)$',
    ),
    tipo: TipoFiltroUsuarioAdmin = Query(
        default='todos',
        pattern='^(todos|usuario|empresa|conductor|premium)$',
    ),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='La fecha desde no puede ser mayor que la fecha hasta.',
        )

    from_clause, where_clause, params = _construir_consulta_usuarios_admin(
        q=q,
        estado=estado,
        tipo=tipo,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )
    params.update(
        {
            'limit': page_size,
            'offset': (page - 1) * page_size,
        }
    )

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
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.phone,
                u.is_company,
                u.company_name,
                u.active,
                u.created_at,
                u.points,
                u.is_premium,
                u.is_driver,
                u.rol_id,
                r.nombre AS rol_nombre,
                u.referred_by_id,
                ref.email AS referred_by_email
            {from_clause}
            {where_clause}
            ORDER BY u.created_at DESC
            OFFSET :offset
            LIMIT :limit
            """
        ),
        params,
    ).mappings().all()

    return ListaUsuariosAdminOut(
        total=int(total or 0),
        page=page,
        page_size=page_size,
        items=[_serializar_usuario(fila) for fila in filas],
    )


@router.get('/exportacion', response_model=list[UsuarioAdminExportOut])
def exportar_usuarios_admin(
    q: str = Query(default='', max_length=255),
    estado: EstadoFiltroUsuarioAdmin = Query(
        default='todos',
        pattern='^(todos|habilitado|inhabilitado)$',
    ),
    tipo: TipoFiltroUsuarioAdmin = Query(
        default='todos',
        pattern='^(todos|usuario|empresa|conductor|premium)$',
    ),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='La fecha desde no puede ser mayor que la fecha hasta.',
        )

    from_clause, where_clause, params = _construir_consulta_usuarios_admin(
        q=q,
        estado=estado,
        tipo=tipo,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )

    filas = db.execute(
        text(
            f"""
            SELECT
                u.id,
                u.email,
                u.first_name,
                u.last_name,
                u.phone,
                u.is_company,
                u.company_name,
                u.active,
                u.created_at,
                u.points,
                u.is_premium,
                u.is_driver
            {from_clause}
            {where_clause}
            ORDER BY u.created_at DESC
            """
        ),
        params,
    ).mappings().all()

    return [
        UsuarioAdminExportOut(
            id=str(fila['id']),
            nombre_completo=' '.join(
                parte
                for parte in [
                    str(fila.get('first_name') or '').strip(),
                    str(fila.get('last_name') or '').strip(),
                ]
                if parte
            )
            or '-',
            correo=str(fila.get('email') or ''),
            telefono=_normalizar_texto(fila.get('phone')),
            empresa=_normalizar_texto(fila.get('company_name')),
            tipo=_obtener_tipo_usuario_exportacion(fila),
            estado='Habilitado' if bool(fila.get('active')) else 'Inhabilitado',
            puntos=_obtener_entero(fila.get('points')),
            fecha_creacion=fila['created_at'],
        )
        for fila in filas
    ]


@router.get('/{usuario_id}', response_model=UsuarioAdminOut)
def obtener_detalle_usuario_admin(
    usuario_id: UUID,
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    fila = _obtener_usuario_por_id(db=db, usuario_id=usuario_id)
    if not fila:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuario no encontrado.',
        )

    return _serializar_usuario(fila)


@router.post('', response_model=UsuarioAdminOut, status_code=status.HTTP_201_CREATED)
def crear_usuario_admin(
    payload: CrearUsuarioAdminIn,
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    email = _normalizar_email(payload.email)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='El correo es obligatorio.',
        )

    if payload.confirm_password is not None and payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='La contraseña y su confirmación no coinciden.',
        )

    existente = db.execute(
        text(
            """
            SELECT id
            FROM conexion_carga.users
            WHERE LOWER(email) = LOWER(:email)
            LIMIT 1
            """
        ),
        {'email': email},
    ).scalar()

    if existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Ya existe un usuario con el correo registrado.',
        )

    referred_by_id = str(payload.referred_by_id) if payload.referred_by_id else None
    if referred_by_id:
        referido = db.execute(
            text(
                """
                SELECT id
                FROM conexion_carga.users
                WHERE id = CAST(:referido_id AS uuid)
                LIMIT 1
                """
            ),
            {'referido_id': referred_by_id},
        ).scalar()

        if not referido:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='El usuario referido no existe.',
            )

    company_name = _normalizar_texto(payload.company_name) if payload.is_company else None
    rol_id = _obtener_rol_admin_id(db) if payload.is_admin else None

    try:
        nuevo_id = db.execute(
            text(
                """
                INSERT INTO conexion_carga.users (
                    email,
                    password_hash,
                    first_name,
                    last_name,
                    phone,
                    is_company,
                    company_name,
                    active,
                    points,
                    referred_by_id,
                    is_premium,
                    is_driver,
                    rol_id,
                    created_at
                )
                VALUES (
                    :email,
                    :password_hash,
                    :first_name,
                    :last_name,
                    :phone,
                    :is_company,
                    :company_name,
                    :active,
                    0,
                    CAST(:referred_by_id AS uuid),
                    :is_premium,
                    :is_driver,
                    :rol_id,
                    NOW()
                )
                RETURNING id
                """
            ),
            {
                'email': email,
                'password_hash': get_password_hash(payload.password),
                'first_name': str(payload.first_name).strip(),
                'last_name': str(payload.last_name).strip(),
                'phone': _normalizar_texto(payload.phone),
                'is_company': bool(payload.is_company),
                'company_name': company_name,
                'active': bool(payload.active),
                'referred_by_id': referred_by_id,
                'is_premium': bool(payload.is_premium),
                'is_driver': bool(payload.is_driver),
                'rol_id': rol_id,
            },
        ).scalar()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='No fue posible crear el usuario. Verifica que el correo no esté repetido.',
        )

    fila = _obtener_usuario_por_id(db=db, usuario_id=nuevo_id)
    if not fila:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='No fue posible recuperar el usuario creado.',
        )

    return _serializar_usuario(fila)


@router.patch('/{usuario_id}', response_model=UsuarioAdminOut)
def actualizar_usuario_admin(
    usuario_id: UUID,
    payload: ActualizarUsuarioAdminIn,
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    actual = _obtener_usuario_por_id(db=db, usuario_id=usuario_id)
    if not actual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuario no encontrado.',
        )

    cambios = payload.model_dump(exclude_unset=True)
    if not cambios:
        return _serializar_usuario(actual)

    if 'confirm_password' in cambios and 'password' not in cambios:
        cambios.pop('confirm_password', None)

    if 'email' in cambios:
        nuevo_email = _normalizar_email(cambios['email'])
        if not nuevo_email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='El correo es obligatorio.',
            )

        repetido = db.execute(
            text(
                """
                SELECT id
                FROM conexion_carga.users
                WHERE LOWER(email) = LOWER(:email)
                  AND id <> CAST(:usuario_id AS uuid)
                LIMIT 1
                """
            ),
            {
                'email': nuevo_email,
                'usuario_id': str(usuario_id),
            },
        ).scalar()

        if repetido:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Ya existe otro usuario con el correo indicado.',
            )

        cambios['email'] = nuevo_email

    if 'first_name' in cambios and not _normalizar_texto(cambios['first_name']):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Los nombres son obligatorios.',
        )

    if 'last_name' in cambios and not _normalizar_texto(cambios['last_name']):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail='Los apellidos son obligatorios.',
        )

    if 'password' in cambios:
        nueva_password = str(cambios.pop('password') or '')
        confirm_password = cambios.pop('confirm_password', None)

        if len(nueva_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='La nueva contraseña debe tener mínimo 8 caracteres.',
            )

        if (
            confirm_password is not None
            and nueva_password != str(confirm_password)
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='La contraseña y su confirmación no coinciden.',
            )

        cambios['password_hash'] = get_password_hash(nueva_password)

    nuevo_is_company = (
        bool(cambios['is_company'])
        if 'is_company' in cambios
        else bool(actual['is_company'])
    )

    if not nuevo_is_company:
        cambios['company_name'] = None
    elif 'company_name' in cambios:
        cambios['company_name'] = _normalizar_texto(cambios['company_name'])

    if 'phone' in cambios:
        cambios['phone'] = _normalizar_texto(cambios['phone'])

    if 'is_admin' in cambios:
        cambios['rol_id'] = _obtener_rol_admin_id(db) if bool(cambios.pop('is_admin')) else None

    if 'referred_by_id' in cambios and cambios['referred_by_id'] is not None:
        referido_id = str(cambios['referred_by_id'])
        if referido_id == str(usuario_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Un usuario no puede referirse a sí mismo.',
            )

        referido = db.execute(
            text(
                """
                SELECT id
                FROM conexion_carga.users
                WHERE id = CAST(:referido_id AS uuid)
                LIMIT 1
                """
            ),
            {'referido_id': referido_id},
        ).scalar()

        if not referido:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='El usuario referido no existe.',
            )

        cambios['referred_by_id'] = referido_id

    if 'referred_by_id' in cambios and cambios['referred_by_id'] is None:
        cambios['referred_by_id'] = None

    columnas_permitidas = {
        'email',
        'first_name',
        'last_name',
        'phone',
        'is_company',
        'company_name',
        'active',
        'is_premium',
        'is_driver',
        'rol_id',
        'referred_by_id',
        'password_hash',
    }

    set_clauses: list[str] = []
    params: dict[str, object] = {'usuario_id': str(usuario_id)}

    for campo, valor in cambios.items():
        if campo not in columnas_permitidas:
            continue

        if campo == 'referred_by_id':
            set_clauses.append('referred_by_id = CAST(:referred_by_id AS uuid)')
            params['referred_by_id'] = valor
            continue

        if campo == 'rol_id':
            set_clauses.append('rol_id = :rol_id')
            params['rol_id'] = valor
            continue

        set_clauses.append(f'{campo} = :{campo}')
        params[campo] = valor

    if not set_clauses:
        return _serializar_usuario(actual)

    try:
        db.execute(
            text(
                f"""
                UPDATE conexion_carga.users
                SET {', '.join(set_clauses)}
                WHERE id = CAST(:usuario_id AS uuid)
                """
            ),
            params,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='No fue posible actualizar el usuario. Verifica que el correo no esté repetido.',
        )

    actualizado = _obtener_usuario_por_id(db=db, usuario_id=usuario_id)
    if not actualizado:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='No fue posible recuperar el usuario actualizado.',
        )

    return _serializar_usuario(actualizado)


@router.patch('/{usuario_id}/estado', response_model=CambiarEstadoUsuarioAdminOut)
def cambiar_estado_usuario_admin(
    usuario_id: UUID,
    payload: CambiarEstadoUsuarioAdminIn,
    db: Session = Depends(get_db),
    _: models.User = Depends(_asegurar_usuario_admin),
):
    actual = _obtener_usuario_por_id(db=db, usuario_id=usuario_id)
    if not actual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Usuario no encontrado.',
        )

    db.execute(
        text(
            """
            UPDATE conexion_carga.users
            SET active = :active
            WHERE id = CAST(:usuario_id AS uuid)
            """
        ),
        {
            'active': bool(payload.active),
            'usuario_id': str(usuario_id),
        },
    )
    db.commit()

    actualizado = _obtener_usuario_por_id(db=db, usuario_id=usuario_id)
    if not actualizado:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='No fue posible recuperar el usuario actualizado.',
        )

    accion = 'habilitado' if payload.active else 'inhabilitado'
    return CambiarEstadoUsuarioAdminOut(
        ok=True,
        message=f'Usuario {accion} correctamente.',
        user=_serializar_usuario(actualizado),
    )
