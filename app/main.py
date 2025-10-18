# app/main.py
"""
Entrypoint principal de la API "Conexión Carga".
Aquí se definen los endpoints y la lógica de verificación por correo.
"""

# ---------------------------------------------------------------------
# 🔹 Importaciones básicas
# ---------------------------------------------------------------------
from __future__ import annotations     # Permite usar anotaciones de tipo adelantadas
from uuid import UUID
import os, time, random, string
from typing import Dict

# ---------------------------------------------------------------------
# 🔹 Dependencias de FastAPI
# ---------------------------------------------------------------------
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# 🔹 Importa tus módulos internos
# ---------------------------------------------------------------------
from . import crud, schemas, models
from .db import Base, engine, get_db
from .security import get_password_hash
from app.services.emailer import send_email  # Servicio SMTP

# ---------------------------------------------------------------------
# 🔹 Configuración desde variables de entorno (.env)
# ---------------------------------------------------------------------
EMAIL_CODE_LENGTH = int(os.getenv("EMAIL_CODE_LENGTH", "6"))           # longitud del código
EMAIL_CODE_TTL_MINUTES = int(os.getenv("EMAIL_CODE_TTL_MINUTES", "15"))# tiempo de validez (min)
EMAIL_RESEND_COOLDOWN_SECONDS = int(os.getenv("EMAIL_RESEND_COOLDOWN_SECONDS", "45"))  # espera entre reenvíos

# ---------------------------------------------------------------------
# 🔹 Estructuras en memoria (solo para demo)
#    En producción podrías usar Redis o base de datos
# ---------------------------------------------------------------------
# Ejemplo de estructura:
# {
#   "user@example.com": { "code": "123456", "expires": 1720000000.0, "attempts": 0 }
# }
_verif_store: Dict[str, dict] = {}

# Control para evitar reenvíos de código muy seguidos
_last_send_epoch: Dict[str, float] = {}

# ---------------------------------------------------------------------
# 🔹 Función auxiliar para generar código aleatorio
# ---------------------------------------------------------------------
def _gen_code(n: int) -> str:
    """Genera un código numérico aleatorio de n dígitos."""
    return "".join(random.choices(string.digits, k=n))

# ---------------------------------------------------------------------
# 🔹 Inicializa DB y app
# ---------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Conexión Carga - Backend", openapi_url="/openapi.json")

# Permitir CORS (útil si el frontend está en otro dominio)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia esto en producción por tus dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------
# 🔹 Health check (para saber si el backend está vivo)
# ---------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}

# ---------------------------------------------------------------------
# 🔹 Endpoint: Listar usuarios
# ---------------------------------------------------------------------
@app.get("/api/users", response_model=list[schemas.UserOut])
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Lista todos los usuarios. Útil para verificar el campo 'active' durante pruebas.
    """
    return crud.get_users(db, skip=skip, limit=limit)

# ---------------------------------------------------------------------
# 🔹 Endpoint: Registro de usuario
# ---------------------------------------------------------------------
@app.post("/api/users/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario y envía un código de verificación por correo.
    """

    # 1️⃣ Validar que el correo no esté ya registrado
    existing = crud.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2️⃣ Crear usuario con contraseña hasheada
    pw_hash = get_password_hash(user.password)
    created = crud.create_user(db, user, pw_hash)

    # 3️⃣ Marcar el usuario como inactivo hasta verificar
    created.active = False
    db.add(created)
    db.commit()
    db.refresh(created)

    # 4️⃣ Prevenir abusos de reenvío de código
    now = time.time()
    last = _last_send_epoch.get(user.email, 0.0)
    if now - last < EMAIL_RESEND_COOLDOWN_SECONDS:
        raise HTTPException(status_code=429, detail="Wait before resending the code")

    # 5️⃣ Generar código y enviar correo
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

    # 6️⃣ Guardar el código en memoria (solo demo)
    _verif_store[user.email] = {
        "code": code,
        "expires": time.time() + (EMAIL_CODE_TTL_MINUTES * 60),
        "attempts": 0,
    }
    _last_send_epoch[user.email] = now

    # 7️⃣ Retornar el usuario (sin contraseña, gracias al esquema UserOut)
    return created

# ---------------------------------------------------------------------
# 🔹 Modelo para la verificación
# ---------------------------------------------------------------------
class VerifyIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=1, max_length=64)

# ---------------------------------------------------------------------
# 🔹 Endpoint: Verificar email con código
# ---------------------------------------------------------------------
@app.post("/api/users/verify")
def verify_email(payload: VerifyIn, db: Session = Depends(get_db)):
    """
    Verifica un código de correo y activa al usuario.
    """

    # 1️⃣ Verificar si existe un código pendiente
    rec = _verif_store.get(payload.email)
    if not rec:
        raise HTTPException(status_code=400, detail="No verification pending for this email")

    # 2️⃣ Verificar si el código está vencido
    if time.time() > rec["expires"]:
        _verif_store.pop(payload.email, None)
        raise HTTPException(status_code=400, detail="Code expired")

    # 3️⃣ Validar coincidencia del código
    if str(payload.code).strip() != str(rec["code"]):
        rec["attempts"] = rec.get("attempts", 0) + 1
        if rec["attempts"] >= 5:
            _verif_store.pop(payload.email, None)
            raise HTTPException(status_code=400, detail="Too many invalid attempts")
        raise HTTPException(status_code=400, detail="Invalid code")

    # 4️⃣ Activar el usuario en la base de datos
    user = crud.get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.active = True
    db.add(user)
    db.commit()
    db.refresh(user)

    # 5️⃣ Eliminar el código (ya usado)
    _verif_store.pop(payload.email, None)

    return {
        "status": "ok",
        "message": "Email verified. User activated.",
        "user_id": str(user.id),
    }

# ---------------------------------------------------------------------
# 🔹 Endpoint: Actualizar usuario
# ---------------------------------------------------------------------
@app.put("/api/users/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: UUID, user: schemas.UserUpdate, db: Session = Depends(get_db)):
    """
    Actualiza datos del usuario, validando correos repetidos.
    """
    if user.email:
        existing = crud.get_user_by_email(db, user.email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=400, detail="Email already in use")

    updated = crud.update_user(db, user_id, user)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    return updated
