from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models
from app.db import get_db
from app.schemas_profile import (
    ActualizarPerfilIn,
    CambiarPasswordPerfilIn,
    MensajePerfilOut,
    PerfilActualOut,
)
from app.security import get_current_user, get_password_hash, verify_password

router = APIRouter(prefix='/api/me/profile', tags=['Mi Perfil'])

BASE_DIR = Path(__file__).resolve().parents[2]
PROFILE_UPLOAD_DIR = BASE_DIR / 'uploads' / 'profile'
PROFILE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

PASSWORD_LETTER_REGEX = re.compile(r'[A-Za-z]')
PASSWORD_NUMBER_REGEX = re.compile(r'\d')
PASSWORD_SYMBOL_REGEX = re.compile(r'[!@#$%^&*(),.?":{}|<>_\-]')
FOTO_MAX_BYTES = 5 * 1024 * 1024
EXTENSIONES_PERMITIDAS = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.webp': 'image/webp',
}


def _normalizar_texto(valor: object, max_length: int | None = None) -> str | None:
    if valor is None:
        return None

    texto = str(valor).strip()
    if not texto:
        return None

    if max_length is not None:
        texto = texto[:max_length].strip()

    return texto or None


def _contrasena_segura(password: str) -> bool:
    if len(password) < 8:
        return False

    return (
        bool(PASSWORD_LETTER_REGEX.search(password))
        and bool(PASSWORD_NUMBER_REGEX.search(password))
        and bool(PASSWORD_SYMBOL_REGEX.search(password))
    )


def _tiene_columna_foto(db: Session) -> bool:
    return bool(
        db.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'conexion_carga'
                      AND table_name = 'users'
                      AND column_name = 'foto'
                )
                """
            )
        ).scalar()
    )


def _asegurar_columna_foto(db: Session) -> None:
    if _tiene_columna_foto(db):
        return

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            'La columna foto aún no existe en conexion_carga.users. '
            'Ejecuta primero el script 20260317_add_foto_to_users.sql.'
        ),
    )


def _resolver_url_foto(foto: str | None) -> str | None:
    if not foto:
        return None

    texto = str(foto).strip()
    if not texto:
        return None

    if texto.startswith('http://') or texto.startswith('https://'):
        return texto

    if texto.startswith('/'):
        return texto

    return f'/uploads/profile/{Path(texto).name}'


def _resolver_archivo_local(foto: str | None) -> Path | None:
    if not foto:
        return None

    nombre_archivo = Path(str(foto)).name
    if not nombre_archivo:
        return None

    ruta = (PROFILE_UPLOAD_DIR / nombre_archivo).resolve()

    try:
        ruta.relative_to(PROFILE_UPLOAD_DIR.resolve())
    except ValueError:
        return None

    return ruta


def _eliminar_archivo_si_controlado(foto: str | None) -> None:
    ruta = _resolver_archivo_local(foto)
    if ruta and ruta.exists():
        ruta.unlink(missing_ok=True)


def _obtener_extension_archivo(archivo: UploadFile) -> str:
    extension = Path(archivo.filename or '').suffix.lower()
    if extension in EXTENSIONES_PERMITIDAS:
        return extension

    content_type = (archivo.content_type or '').lower()
    for extension_permitida, mime in EXTENSIONES_PERMITIDAS.items():
        if content_type == mime:
            return extension_permitida

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail='La foto debe estar en formato JPG, PNG o WEBP.',
    )


def _obtener_perfil_actual(db: Session, user_id: str) -> PerfilActualOut:
    foto_select = 'u.foto' if _tiene_columna_foto(db) else 'NULL::text AS foto'

    row = db.execute(
        text(
            f"""
            SELECT
                u.id,
                u.first_name,
                u.last_name,
                TRIM(COALESCE(u.first_name, '') || ' ' || COALESCE(u.last_name, '')) AS full_name,
                u.email,
                u.phone,
                u.is_company,
                u.company_name,
                u.active,
                u.created_at,
                {foto_select}
            FROM conexion_carga.users u
            WHERE u.id = CAST(:user_id AS uuid)
            LIMIT 1
            """
        ),
        {'user_id': str(user_id)},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Usuario no encontrado.')

    foto = _normalizar_texto(row.get('foto'))
    company_name = _normalizar_texto(row.get('company_name'))
    is_company = bool(row.get('is_company'))

    return PerfilActualOut(
        id=str(row['id']),
        first_name=str(row.get('first_name') or '').strip(),
        last_name=str(row.get('last_name') or '').strip(),
        full_name=str(row.get('full_name') or '').strip(),
        email=str(row.get('email') or '').strip(),
        phone=_normalizar_texto(row.get('phone')),
        is_company=is_company,
        company_name=company_name if is_company else None,
        active=bool(row.get('active')),
        created_at=row['created_at'],
        foto=foto,
        foto_url=_resolver_url_foto(foto),
    )


@router.get('', response_model=PerfilActualOut)
def obtener_mi_perfil(
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    return _obtener_perfil_actual(db, str(current.id))


@router.put('', response_model=PerfilActualOut)
def actualizar_mi_perfil(
    payload: ActualizarPerfilIn,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    first_name = _normalizar_texto(payload.first_name, 120)
    last_name = _normalizar_texto(payload.last_name, 120)

    if not first_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Los nombres son obligatorios.')

    if not last_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Los apellidos son obligatorios.')

    current.first_name = first_name
    current.last_name = last_name
    current.phone = _normalizar_texto(payload.phone, 30)
    current.company_name = (
        _normalizar_texto(payload.company_name, 255)
        if bool(current.is_company)
        else None
    )

    db.add(current)
    db.commit()

    return _obtener_perfil_actual(db, str(current.id))


@router.put('/password', response_model=MensajePerfilOut)
def cambiar_mi_password(
    payload: CambiarPasswordPerfilIn,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    if not verify_password(payload.password_actual, current.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='La contraseña actual no es correcta.',
        )

    if payload.nueva_password != payload.confirmar_nueva_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='La confirmación de la nueva contraseña no coincide.',
        )

    if payload.nueva_password == payload.password_actual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='La nueva contraseña debe ser diferente a la actual.',
        )

    if not _contrasena_segura(payload.nueva_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                'La nueva contraseña debe tener mínimo 8 caracteres e incluir '
                'letras, números y un símbolo.'
            ),
        )

    current.password_hash = get_password_hash(payload.nueva_password)
    db.add(current)
    db.commit()

    return MensajePerfilOut(message='La contraseña se actualizó correctamente.')


@router.post('/photo', response_model=PerfilActualOut)
async def subir_mi_foto(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    _asegurar_columna_foto(db)

    if not archivo.content_type or not archivo.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='La foto debe ser un archivo de imagen válido.',
        )

    extension = _obtener_extension_archivo(archivo)
    contenido = await archivo.read()

    if not contenido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='La foto seleccionada está vacía.',
        )

    if len(contenido) > FOTO_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='La foto no debe superar 5 MB.',
        )

    perfil_actual = _obtener_perfil_actual(db, str(current.id))

    nombre_archivo = f'{current.id}-{uuid4().hex}{extension}'
    ruta_archivo = PROFILE_UPLOAD_DIR / nombre_archivo
    ruta_archivo.write_bytes(contenido)

    foto_guardada = f'/uploads/profile/{nombre_archivo}'

    db.execute(
        text(
            """
            UPDATE conexion_carga.users
            SET foto = :foto
            WHERE id = CAST(:user_id AS uuid)
            """
        ),
        {'foto': foto_guardada, 'user_id': str(current.id)},
    )
    db.commit()

    _eliminar_archivo_si_controlado(perfil_actual.foto)

    return _obtener_perfil_actual(db, str(current.id))


@router.delete('/photo', response_model=PerfilActualOut)
def eliminar_mi_foto(
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    _asegurar_columna_foto(db)

    perfil_actual = _obtener_perfil_actual(db, str(current.id))

    db.execute(
        text(
            """
            UPDATE conexion_carga.users
            SET foto = NULL
            WHERE id = CAST(:user_id AS uuid)
            """
        ),
        {'user_id': str(current.id)},
    )
    db.commit()

    _eliminar_archivo_si_controlado(perfil_actual.foto)

    return _obtener_perfil_actual(db, str(current.id))
