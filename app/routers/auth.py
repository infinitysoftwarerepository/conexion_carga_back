# app/routers/auth.py
"""
Rutas de autenticación (login).
Retorna: { "token": "...", "user": { ... } }
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app import crud, schemas
from app.db import get_db
from app.security import verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# ==== Schemas locales ====
class LoginIn(BaseModel):
    email: EmailStr
    password: str

class LoginOut(BaseModel):
    token: str
    user: schemas.UserOut

@router.post("/login", response_model=LoginOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    """
    Autentica por email y password.
    Requisitos:
      - usuario exista
      - usuario.active = True (ya verificado)
      - password correcta
    """
    user = crud.get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # usuario debe estar activo (ya verificó correo)
    if not user.active:
        raise HTTPException(status_code=403, detail="Email not verified")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # sub = email; puedes usar user.id si prefieres
    token = create_access_token({"sub": user.email})

    return LoginOut(token=token, user=schemas.UserOut.model_validate(user, from_attributes=True))
