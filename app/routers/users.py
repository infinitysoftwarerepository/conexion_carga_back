# app/routers/users.py
"""
Módulo de rutas de usuarios.
Contiene:
- registro
- verificación de email
- actualización
- /me (perfil del usuario con token)
"""
from __future__ import annotations
import os, time, random, string
from typing import Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import get_db
from app.security import get_password_hash, get_current_user
from app.services.emailer import send_email

# === Config ===
EMAIL_CODE_LENGTH = int(os.getenv("EMAIL_CODE_LENGTH", "6"))
EMAIL_CODE_TTL_MINUTES = int(os.getenv("EMAIL_CODE_TTL_MINUTES", "5"))
EMAIL_RESEND_COOLDOWN_SECONDS = int(os.getenv("EMAIL_RESEND_COOLDOWN_SECONDS", "45"))

# === Stores in-memory (demo) ===
_verif_store: Dict[str, dict] = {}
_last_send_epoch: Dict[str, float] = {}

def _gen_code(n: int) -> str:
    return "".join(random.choices(string.digits, k=n))

router = APIRouter(prefix="/api/users", tags=["Users"])

# ==== Modelos internos ====
class VerifyIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=1, max_length=64)

@router.get("", response_model=list[schemas.UserOut])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)

@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    pw_hash = get_password_hash(user.password)
    created = crud.create_user(db, user, pw_hash)
    created.active = False
    db.add(created); db.commit(); db.refresh(created)

    now = time.time()
    last = _last_send_epoch.get(user.email, 0.0)
    if now - last < EMAIL_RESEND_COOLDOWN_SECONDS:
        raise HTTPException(status_code=429, detail="Wait before resending the code")

    code = _gen_code(EMAIL_CODE_LENGTH)
    subject = "Verification code - Conexión Carga"
    text = f"Hola,\nTu código de verificación es: {code}\nVence en {EMAIL_CODE_TTL_MINUTES} minutos."
    html = f"""
        <p>Hola,</p>
        <p>Tu código de verificación es:
           <strong style='font-size:20px;letter-spacing:2px'>{code}</strong></p>
        <p>Vence en <strong>{EMAIL_CODE_TTL_MINUTES}</strong> minutos.</p>
        <p style='color:#666;font-size:12px'>Si no solicitaste este código, ignora este correo.</p>
    """
    try:
        send_email(user.email, subject, text, html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email send failed: {e}")

    _verif_store[user.email] = {
        "code": code,
        "expires": time.time() + (EMAIL_CODE_TTL_MINUTES * 60),
        "attempts": 0,
    }
    _last_send_epoch[user.email] = now
    return created

@router.post("/verify")
def verify_email(payload: VerifyIn, db: Session = Depends(get_db)):
    rec = _verif_store.get(payload.email)
    if not rec:
        raise HTTPException(status_code=400, detail="No verification pending for this email")

    if time.time() > rec["expires"]:
        _verif_store.pop(payload.email, None)
        raise HTTPException(status_code=400, detail="Code expired")

    if str(payload.code).strip() != str(rec["code"]):
        rec["attempts"] = rec.get("attempts", 0) + 1
        if rec["attempts"] >= 5:
            _verif_store.pop(payload.email, None)
            raise HTTPException(status_code=400, detail="Too many invalid attempts")
        raise HTTPException(status_code=400, detail="Invalid code")

    user = crud.get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.active = True
    db.add(user); db.commit(); db.refresh(user)

    _verif_store.pop(payload.email, None)
    return {"status": "ok", "message": "Email verified. User activated.", "user_id": str(user.id)}

@router.get("/me", response_model=schemas.UserOut)
def get_me(current: schemas.UserOut = Depends(get_current_user)):
    """Devuelve el perfil del usuario autenticado (token en Authorization: Bearer)."""
    return current

@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: UUID, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    if user.email:
        existing = crud.get_user_by_email(db, user.email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=400, detail="Email already in use")
    updated = crud.update_user(db, user_id, user)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return updated
