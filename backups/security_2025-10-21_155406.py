from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
# app/security.py
"""
Utilidades de seguridad:
- Hash/verify de contraseñas (bcrypt)
- Creación y verificación de JWT (HS256)
- Dependencia `get_current_user` para rutas protegidas
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db import get_db
from app import crud, schemas

# === Config de JWT ===
JWT_SECRET = os.getenv("JWT_SECRET", "change_me_please")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
ALGORITHM = "HS256"

# === Password hashing (bcrypt) ===
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Genera hash seguro para almacenar en DB."""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Compara contraseña en texto con su hash."""
    return pwd_context.verify(plain, hashed)

# === OAuth bearer (lee "Authorization: Bearer <token>") ===
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")  # solo para el flow de docs

def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    """Crea un JWT firmando `data` con expiración."""
    to_encode = data.copy()
    exp = datetime.utcnow() + timedelta(minutes=expires_minutes or JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": exp})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> schemas.UserOut:
    """Decodifica el token y devuelve el usuario actual (400/401 si algo falla)."""
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if not email:
            raise cred_exc
    except JWTError:
        raise cred_exc

    user = crud.get_user_by_email(db, email)
    if not user:
        raise cred_exc
    if not user.active:
        raise HTTPException(status_code=403, detail="User is not active")

    # devolvemos el esquema limpio
    return schemas.UserOut.model_validate(user, from_attributes=True)
