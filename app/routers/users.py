"""
Users router: Registro de usuario + envío de código de verificación por email.

Flujo:
1) Valida JSON contra schemas.UserCreate (contraseñas iguales, lógica company_name).
2) Checa duplicado de email (409 si existe).
3) Hashea password y crea el usuario (crud.create_user).
4) Controla cooldown para evitar spam de correos.
5) Genera código numérico y lo envía por email (texto + HTML).
6) Devuelve respuesta (incluye 'code' SOLO para pruebas; en producción, quítalo).

Requiere:
- app/db.py con get_db (Session)
- app/crud.py (get_user_by_email, create_user)
- app/security.py con get_password_hash
- app/services/emailer.py con send_email
"""

from __future__ import annotations

import os
import time
import random
import string
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app import crud, schemas
from app.security import get_password_hash
from app.services.emailer import send_email

# Parámetros desde .env (con defaults)
EMAIL_CODE_LENGTH = int(os.getenv("EMAIL_CODE_LENGTH", "6"))
EMAIL_CODE_TTL_MINUTES = int(os.getenv("EMAIL_CODE_TTL_MINUTES", "15"))
EMAIL_RESEND_COOLDOWN_SECONDS = int(os.getenv("EMAIL_RESEND_COOLDOWN_SECONDS", "45"))

# Memoria simple para cooldown por email (en producción: DB/Redis)
_last_send_epoch: Dict[str, float] = {}

router = APIRouter(prefix="/api/users", tags=["users"])


def _gen_code(n: int) -> str:
    """Genera un código numérico de n dígitos (p. ej. '123456')."""
    return "".join(random.choices(string.digits, k=n))


@router.post("/register", summary="Register User")
def register_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    # 0) Evitar duplicados
    if crud.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    # 1) Hash de la contraseña
    password_hash = get_password_hash(payload.password)

    # 2) Crear usuario (crud ya normaliza company_name si is_company=False)
    user = crud.create_user(db, payload, password_hash)

    # 3) Anti-spam: cooldown por email
    now = time.time()
    last = _last_send_epoch.get(payload.email, 0.0)
    if now - last < EMAIL_RESEND_COOLDOWN_SECONDS:
        raise HTTPException(status_code=429, detail="Wait before resending the code")

    # 4) Generar código
    code = _gen_code(EMAIL_CODE_LENGTH)

    # 5) Enviar email
    subject = "Verification code - Conexión Carga"
    text = (
        f"Your verification code is: {code}\n"
        f"It expires in {EMAIL_CODE_TTL_MINUTES} minutes.\n\n"
        f"If you didn't request this code, please ignore this email."
    )
    html = f"""
    <p>Your verification code is:
       <strong style="font-size:20px;letter-spacing:2px">{code}</strong></p>
    <p>It expires in <strong>{EMAIL_CODE_TTL_MINUTES}</strong> minutes.</p>
    <p style="color:#666;font-size:12px">If you didn't request this code, please ignore this email.</p>
    """
    try:
        send_email(payload.email, subject, text, html)
    except Exception as e:
        # Política simple: si falla el envío, devolvemos 500; el usuario ya quedó creado.
        # Puedes cambiar a "estado pendiente" y reintentar luego.
        raise HTTPException(status_code=500, detail=f"Email send failed: {e}")

    _last_send_epoch[payload.email] = now

    # 6) Respuesta: devolvemos el 'code' SOLO para pruebas; quítalo en prod.
    return {
        "status": "ok",
        "user_id": str(user.id),
        "email": user.email,
        "is_company": user.is_company,
        "company_name": user.company_name,  # será None si is_company=False
        "message": "Verification code sent to email",
        "code": code,  # ⚠️ quitar en producción
    }
