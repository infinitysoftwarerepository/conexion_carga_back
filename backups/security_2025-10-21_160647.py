# app/security.py
# ============================================================
# Utilidades de seguridad:
# - Hash y verificación de contraseñas (passlib/bcrypt)
# - Creación de tokens JWT
# ============================================================

from __future__ import annotations  # <= Debe ir PRIMERO en el archivo

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import jwt
from passlib.context import CryptContext

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "change_me_please")
JWT_ALG = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# Contexto de passlib para bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ------------------------------------------------------------
# Contraseñas
# ------------------------------------------------------------
def get_password_hash(password: str) -> str:
    """Devuelve el hash seguro de la contraseña."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, password_hash: str) -> bool:
    """Compara contraseña en texto plano vs. hash almacenado."""
    return pwd_context.verify(plain_password, password_hash)

# ------------------------------------------------------------
# JWT
# ------------------------------------------------------------
def create_access_token(
    subject: str | int,
    expires_minutes: int | None = None,
    extra_claims: Dict[str, Any] | None = None,
) -> str:
    """
    Crea un JWT de acceso.
    - subject: normalmente el ID del usuario
    - expires_minutes: por defecto toma JWT_EXPIRE_MINUTES
    - extra_claims: claims adicionales que quieras meter al token
    """
    if expires_minutes is None:
        expires_minutes = JWT_EXPIRE_MINUTES

    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=expires_minutes)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    return token
