# app/main.py
from __future__ import annotations  # ayuda a posponer anotaciones si las usas en otros archivos

from uuid import UUID
import os, time, random, string

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud, schemas, models
from .db import Base, engine, get_db
from .security import get_password_hash
from app.services.emailer import send_email

# Config de verificación
EMAIL_CODE_LENGTH = int(os.getenv("EMAIL_CODE_LENGTH", "6"))
EMAIL_CODE_TTL_MINUTES = int(os.getenv("EMAIL_CODE_TTL_MINUTES", "15"))
EMAIL_RESEND_COOLDOWN_SECONDS = int(os.getenv("EMAIL_RESEND_COOLDOWN_SECONDS", "45"))
_last_send_epoch: dict[str, float] = {}

def _gen_code(n: int) -> str:
    return "".join(random.choices(string.digits, k=n))

# Crea tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Conexion Carga - Backend", openapi_url="/openapi.json")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health
@app.get("/health")
def health():
    return {"ok": True}

# Users
@app.get("/api/users", response_model=list[schemas.UserOut])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)

@app.post("/api/users/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    pw_hash = get_password_hash(user.password)
    created = crud.create_user(db, user, pw_hash)

    # Cooldown anti-abuso
    now = time.time()
    last = _last_send_epoch.get(user.email, 0.0)
    if now - last < EMAIL_RESEND_COOLDOWN_SECONDS:
        raise HTTPException(status_code=429, detail="Wait before resending the code")

    # Código + correo
    code = _gen_code(EMAIL_CODE_LENGTH)
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
        send_email(user.email, subject, text, html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email send failed: {e}")

    _last_send_epoch[user.email] = now
    return created

@app.put("/api/users/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: UUID, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    if user.email:
        existing = crud.get_user_by_email(db, user.email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Email already in use by another user")

    updated = crud.update_user(db, user_id, user)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated
