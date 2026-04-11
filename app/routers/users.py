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

from datetime import datetime
from typing import Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.db import get_db
from app.security import get_current_user, get_password_hash
from app.services.emailer import send_email
from app.utils.user_contact import resolve_document_and_phone

router = APIRouter(prefix="/api/users", tags=["Users"])


class ReloadCodeIn(BaseModel):
    email: EmailStr


class VerifyCodeIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=1, max_length=64)


def _resolve_user_contact_for_register(user: schemas.UserCreate) -> schemas.UserCreate:
    data = user.model_dump()

    try:
        document, phone = resolve_document_and_phone(
            document=user.document,
            phone=user.phone,
            phone_code=user.phone_code,
            phone_number=user.phone_number,
            require_document=True,
            require_phone=False,
            allow_legacy_document_from_phone=True,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    data['document'] = document
    data['phone'] = phone
    data.pop('phone_code', None)
    data.pop('phone_number', None)
    return schemas.UserCreate(**data)


def _resolve_user_contact_for_update(
    current_user: models.User,
    user: schemas.UserUpdate,
) -> schemas.UserUpdate:
    data = user.model_dump(exclude_unset=True)
    if not any(
        campo in data for campo in ('document', 'phone', 'phone_code', 'phone_number')
    ):
        return user

    try:
        document, phone = resolve_document_and_phone(
            document=data.get('document') if 'document' in data else None,
            phone=data.get('phone') if 'phone' in data else None,
            phone_code=data.get('phone_code') if 'phone_code' in data else None,
            phone_number=data.get('phone_number') if 'phone_number' in data else None,
            require_document=False,
            require_phone=False,
            allow_legacy_document_from_phone='phone' in data and 'document' not in data,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if 'document' not in data and document is None:
        document = getattr(current_user, 'document', None)

    if not any(campo in data for campo in ('phone', 'phone_code', 'phone_number')):
        phone = getattr(current_user, 'phone', None)

    data['document'] = document
    data['phone'] = phone
    data.pop('phone_code', None)
    data.pop('phone_number', None)
    return schemas.UserUpdate(**data)


@router.get("", response_model=list[schemas.UserOut])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)


@router.post(
    "/register",
    response_model=schemas.UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    user = _resolve_user_contact_for_register(user)

    existing = crud.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Correo ya registrado")

    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    ref_id = None
    if user.referrer_email:
        ref = crud.get_user_by_email(db, str(user.referrer_email))
        if not ref:
            raise HTTPException(status_code=400, detail="Referrer email does not exist")
        ref_id = ref.id

    pw_hash = get_password_hash(user.password)
    created = crud.create_user(db, user, pw_hash, referred_by_id=ref_id)
    created.active = False
    db.add(created)
    db.commit()
    db.refresh(created)

    code = crud.create_verification_code(db, created)

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


@router.post("/reload-code", summary="Reenviar código de verificación")
def reload_code(
    payload: ReloadCodeIn,
    db: Session = Depends(get_db),
):
    user = crud.get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

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

    verif.used = True
    was_active = bool(user.active)
    user.active = True

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


@router.get("/me", response_model=schemas.UserOut)
def get_me(current: schemas.UserOut = Depends(get_current_user)):
    return current


@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: UUID, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    current = crud.get_user(db, user_id)
    if not current:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email:
        existing = crud.get_user_by_email(db, user.email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=400, detail="Correo en uso")

    user = _resolve_user_contact_for_update(current, user)
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
                models.User.active == True,
            )
            .count()
        )

        rows.append({
            "email": u.email,
            "document": getattr(u, 'document', None),
            "phone": u.phone,
            "points": pts,
        })

    rows.sort(key=lambda x: x["points"], reverse=True)
    return rows
