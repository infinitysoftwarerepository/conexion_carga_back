# app/routers/users.py
"""
Rutas de usuarios:
- Registro
- Reenvío de código de verificación
- Verificación de email
- Perfil /me
- Actualización de usuario
"""

from __future__ import annotations
from typing import Dict
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app import crud, schemas, models
from app.db import get_db
from app.security import get_password_hash, get_current_user
from app.services.emailer import send_email

router = APIRouter(prefix="/api/users", tags=["Users"])


# ==========================
#   Esquemas internos
# ==========================

class ReloadCodeIn(BaseModel):
    email: EmailStr


class VerifyCodeIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=1, max_length=64)


# ==========================
#   Listado de usuarios
# ==========================

@router.get("", response_model=list[schemas.UserOut])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)


# ==========================
#   Registro de usuario
# ==========================

@router.post(
    "/register",
    response_model=schemas.UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # 1) Email duplicado
    existing = crud.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Correo ya registrado")

    # 2) Validar contraseñas iguales
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # 3) Resolver referidor (opcional)
    ref_id = None
    if user.referrer_email:
        ref = crud.get_user_by_email(db, str(user.referrer_email))
        if not ref:
            raise HTTPException(status_code=400, detail="Referrer email does not exist")
        ref_id = ref.id

    # 4) Crear usuario con hash y referidor
    pw_hash = get_password_hash(user.password)
    created = crud.create_user(db, user, pw_hash, referred_by_id=ref_id)
    created.active = False
    db.add(created)
    db.commit()
    db.refresh(created)

    # 5) Crear código de verificación en BD
    code = crud.create_verification_code(db, created)

    # 6) Enviar email (reutilizamos send_email)
    subject = "Código de verificación - Conexión Carga"
    text = (
        f"Hola {created.first_name},\n\n"
        f"Tu código de verificación es: {code}\n"
        "Este código vence en 5 minutos.\n\n"
        "Si no solicitaste este código, ignora este correo."
    )
    html = f"""
        <p>Hola {created.first_name},</p>
        <p>Tu código de verificación es:
           <strong style='font-size:20px;letter-spacing:2px'>{code}</strong></p>
        <p>El código vence en <strong>5 minutos</strong>.</p>
        <p style='color:#666;font-size:12px'>
           Si no solicitaste este código, puedes ignorar este correo.
        </p>
    """

    try:
        send_email(created.email, subject, text, html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email send failed: {e}")

    return created


# ==========================
#   Reenviar código
# ==========================

@router.post("/reload-code", summary="Reenviar código de verificación")
def reload_code(
    payload: ReloadCodeIn,
    db: Session = Depends(get_db),
):
    user = crud.get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Genera nuevo código en BD (invalida los anteriores)
    code = crud.create_verification_code(db, user)

    subject = "Nuevo código de verificación - Conexión Carga"
    text = (
        f"Hola {user.first_name},\n\n"
        f"Tu nuevo código de verificación es: {code}\n"
        "Este código vence en 5 minutos.\n\n"
        "Si no solicitaste este código, ignora este correo."
    )
    html = f"""
        <p>Hola {user.first_name},</p>
        <p>Tu nuevo código de verificación es:
           <strong style='font-size:20px;letter-spacing:2px'>{code}</strong></p>
        <p>El código vence en <strong>5 minutos</strong>.</p>
        <p style='color:#666;font-size:12px'>
           Si no solicitaste este código, puedes ignorar este correo.
        </p>
    """

    try:
        send_email(user.email, subject, text, html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email send failed: {e}")

    return {"detail": "Nuevo código enviado al correo"}


# ==========================
#   Verificar email
# ==========================

@router.post("/verify", summary="Validar código de verificación")
def verify_user(
    payload: VerifyCodeIn,
    db: Session = Depends(get_db),
):
    user = crud.get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    verif = (
        db.query(models.VerificationCode)
        .filter(
            models.VerificationCode.user_id == user.id,
            models.VerificationCode.code == payload.code,
            models.VerificationCode.used == False,
        )
        .first()
    )

    if not verif:
        raise HTTPException(status_code=400, detail="Código inválido")

    if verif.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="El código ha expirado")

    # marcar código como usado y activar usuario
    verif.used = True
    was_active = bool(user.active)
    user.active = True

    # premiar referidor si aplica y aún no fue premiado
    if not was_active and user.referred_by_id and not getattr(user, "referral_rewarded", False):
        ref = db.query(models.User).get(user.referred_by_id)
        if ref:
            ref.points = int(ref.points or 0) + 1
            user.referral_rewarded = True
            db.add(ref)

    db.add(user)
    db.add(verif)
    db.commit()
    db.refresh(user)

    return {
        "detail": "Cuenta verificada exitosamente",
        "user_id": str(user.id),
    }


# ==========================
#   Perfil actual
# ==========================

@router.get("/me", response_model=schemas.UserOut)
def get_me(current: schemas.UserOut = Depends(get_current_user)):
    """Devuelve el perfil del usuario autenticado (token Bearer)."""
    return current


# ==========================
#   Actualizar usuario
# ==========================

@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: UUID, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    if user.email:
        existing = crud.get_user_by_email(db, user.email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=400, detail="Correo en uso")
    updated = crud.update_user(db, user_id, user)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated

@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    """
    Retorna lista de usuarios + puntos calculados dinámicamente:
    puntos = cantidad de usuarios activos cuyo referred_by_id = id del usuario
    """
    users = db.query(models.User).all()

    rows = []
    for u in users:
        pts = (
            db.query(models.User)
            .filter(
                models.User.referred_by_id == u.id,
                models.User.active == True   # Solo cuenta referidos ACTIVOS
            )
            .count()
        )

        rows.append({
            "email": u.email,
            "phone": u.phone,
            "points": pts,
        })

    # ordenar por puntos desc
    rows.sort(key=lambda x: x["points"], reverse=True)

    return rows
