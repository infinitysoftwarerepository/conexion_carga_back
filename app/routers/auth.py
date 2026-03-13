# app/routers/auth.py
"""
Rutas de autenticacion.

- /login y /login-form mantienen compatibilidad con la app movil.
- /login-admin agrega control de acceso para panel web administrativo.
- /password/forgot envia codigo para recuperacion de contrasena.
- /password/reset restablece la contrasena usando codigo.
- /logout expone un cierre de sesion no disruptivo para la web.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.db import get_db
from app.security import create_access_token, get_password_hash, verify_password
from app.services.emailer import send_email

router = APIRouter(prefix="/api/auth", tags=["Auth"])

ROL_ADMINISTRADOR = "Administrador"
EMAIL_CODE_TTL_MINUTES = int(os.getenv("EMAIL_CODE_TTL_MINUTES", "5"))
EMAIL_RESEND_COOLDOWN_SECONDS = int(os.getenv("EMAIL_RESEND_COOLDOWN_SECONDS", "45"))

PASSWORD_LETTER_REGEX = re.compile(r"[A-Za-z]")
PASSWORD_NUMBER_REGEX = re.compile(r"\d")
PASSWORD_SYMBOL_REGEX = re.compile(r"[!@#$%^&*(),.?\":{}|<>_\-]")

# Fallback temporal para no bloquear la adopcion del login web antes de ejecutar
# la migracion de roles. Se recomienda reemplazar con WEB_ADMIN_EMAILS y/o
# con la tabla conexion_carga.rol + users.rol_id.
EMAILS_ADMIN_FALLBACK = {
    "daniloramirez0818@gmail.com",
    "ddgaviriaz@unal.edu.co",
}

_password_last_send_epoch: dict[str, float] = {}


def _normalizar_email(email: str) -> str:
    return email.strip().lower()


def _contrasena_segura(password: str) -> bool:
    if len(password) < 8:
        return False

    return (
        bool(PASSWORD_LETTER_REGEX.search(password))
        and bool(PASSWORD_NUMBER_REGEX.search(password))
        and bool(PASSWORD_SYMBOL_REGEX.search(password))
    )


def _obtener_emails_admin_configurados() -> set[str]:
    raw = os.getenv("WEB_ADMIN_EMAILS", "")
    return {email.strip().lower() for email in raw.split(",") if email.strip()}


def _usuario_tiene_rol_admin_en_bd(
    db: Session,
    user_id: UUID | str,
) -> Optional[bool]:
    """
    Valida rol Administrador usando esquema BD (rol + users.rol_id).

    Retorna:
    - True/False: si la estructura existe y pudo evaluarse.
    - None: si la estructura aun no existe.
    """
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

        if not estructura["tiene_tabla_rol"] or not estructura["tiene_columna_rol_id"]:
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
            {"user_id": str(user_id)},
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

    return email.strip().lower() in emails_admin


def _serializar_usuario_admin(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "is_company": bool(user.is_company),
        "company_name": user.company_name,
        "active": bool(user.active),
        "points": int(user.points or 0),
        "is_premium": bool(user.is_premium),
        "rol": ROL_ADMINISTRADOR,
        "authority": ["admin"],
    }


@router.post(
    "/login",
    response_model=schemas.TokenOut,
    response_model_exclude_none=True,
    summary="Login (JSON)",
)
def login_json(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    """
    Inicia sesion con JSON:
      { "email": "...", "password": "..." }
    """
    user = crud.get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )

    token = create_access_token({"sub": str(user.id)})
    user_out = schemas.UserOut.model_validate(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_out,
    }


@router.post(
    "/login-form",
    response_model=schemas.TokenOut,
    response_model_exclude_none=True,
    summary="Login (form-url-encoded)",
)
def login_form(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Variante para pruebas desde Swagger o formularios application/x-www-form-urlencoded.
    """
    user = crud.get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )

    token = create_access_token({"sub": str(user.id)})
    user_out = schemas.UserOut.model_validate(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_out,
    }


@router.post(
    "/login-admin",
    summary="Login administrativo web",
)
def login_admin(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    """
    Login exclusivo para panel administrativo web.
    Reutiliza credenciales de conexion_carga.users y exige Administrador.
    """
    user = crud.get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo. No puede acceder al panel administrativo.",
        )

    if not _usuario_es_admin(db=db, email=user.email, user_id=user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene permisos de Administrador.",
        )

    token = create_access_token({"sub": str(user.id)})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _serializar_usuario_admin(user),
    }


@router.post(
    "/password/forgot",
    summary="Enviar código de recuperación",
)
def forgot_password(
    payload: schemas.PasswordForgotIn,
    db: Session = Depends(get_db),
):
    """
    Solicita código de verificación para restablecer contraseña.
    Compatible con flujo de la app móvil y con verification_codes en BD.
    """
    email = _normalizar_email(str(payload.email))
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un usuario con ese correo electrónico.",
        )

    now = time.time()
    last_send = _password_last_send_epoch.get(email, 0.0)
    elapsed = now - last_send
    if elapsed < EMAIL_RESEND_COOLDOWN_SECONDS:
        wait_seconds = max(1, int(EMAIL_RESEND_COOLDOWN_SECONDS - elapsed))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Espera {wait_seconds} segundos antes de solicitar un nuevo código.",
        )

    code = crud.create_verification_code(db, user)
    subject = "Código de recuperación - Conexión Carga"
    text_body = (
        "Hola,\n"
        f"Tu código de recuperación es: {code}\n"
        f"Este código vence en {EMAIL_CODE_TTL_MINUTES} minutos.\n"
        "Si no solicitaste este código, ignora este correo."
    )
    html_body = f"""
        <p>Hola {user.first_name},</p>
        <p>Tu código de recuperación es:
           <strong style='font-size:20px;letter-spacing:2px'>{code}</strong>
        </p>
        <p>Este código vence en <strong>{EMAIL_CODE_TTL_MINUTES}</strong> minutos.</p>
        <p style='color:#666;font-size:12px'>
          Si no solicitaste este código, ignora este correo.
        </p>
    """

    try:
        send_email(
            to_email=user.email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible enviar el código de recuperación. Inténtalo nuevamente.",
        )

    _password_last_send_epoch[email] = now

    return {"ok": True, "message": "Código enviado correctamente."}


@router.post(
    "/password/reset",
    summary="Restablecer contraseña",
)
def reset_password(
    payload: schemas.PasswordResetIn,
    db: Session = Depends(get_db),
):
    """
    Restablece contraseña usando email + código + nueva contraseña.
    Compatible con flujo móvil y con códigos persistidos en BD.
    """
    email = _normalizar_email(str(payload.email))
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un usuario con ese correo electrónico.",
        )

    verif = (
        db.query(models.VerificationCode)
        .filter(
            models.VerificationCode.user_id == user.id,
            models.VerificationCode.code == str(payload.code).strip(),
            models.VerificationCode.used.is_(False),
        )
        .first()
    )

    if not verif or verif.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código ingresado no es válido o expiró.",
        )

    if not _contrasena_segura(payload.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "La contraseña debe tener mínimo 8 caracteres, letras, "
                "números y al menos un símbolo."
            ),
        )

    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe ser diferente a la actual.",
        )

    verif.used = True
    user.password_hash = get_password_hash(payload.new_password)

    db.add(user)
    db.add(verif)
    db.commit()

    return {"ok": True, "message": "Contraseña actualizada correctamente."}


@router.post("/logout", summary="Logout administrativo")
def logout_admin():
    """
    Endpoint no disruptivo para cerrar sesion desde frontend web.
    El cierre efectivo del token se maneja del lado cliente.
    """
    return {"ok": True}
