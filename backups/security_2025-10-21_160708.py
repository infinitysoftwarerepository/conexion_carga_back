# app/security.py
# ============================================================
# Utilidades de seguridad:
# - Hash y verificación de contraseñas (passlib/bcrypt)
# - Creación/decodificación de JWT
# - Dependencia FastAPI: get_current_user
# ============================================================

from __future__ import annotations  # 👈 Debe ser la PRIMERA línea real

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

# Para la dependencia get_current_user
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
JWT_SECRET = os.getenv("JWT_SECRET", "change_me_please")
JWT_ALG = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# OAuth2 password flow (solo para que Swagger sepa el endpoint de login)
# No afecta al funcionamiento real del decode.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

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
    expires_minutes: Optional[int] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
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


def decode_token(token: str) -> Dict[str, Any]:
    """Decodifica el JWT y devuelve el payload o lanza HTTP 401/403."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError:
        raise credentials_exc
    if not isinstance(payload, dict) or "sub" not in payload:
        raise credentials_exc
    return payload


# ------------------------------------------------------------
# Dependencia: usuario autenticado desde el token
# ------------------------------------------------------------
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(lambda: __import__("app.db", fromlist=["get_db"]).db.get_db().__next__()),
):
    """
    Devuelve el usuario autenticado a partir del token Bearer.
    Importamos `get_db` y `crud` de forma perezosa para evitar ciclos.
    """
    # Decodificar token
    payload = decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject")

    # Import lazy para evitar ciclos
    crud = __import__("app.crud", fromlist=["get_user"])  # type: ignore

    # Traer user por ID (UUID en tu modelo). Aceptamos str/int.
    try:
        from uuid import UUID
        uid = UUID(str(user_id))
    except Exception:
        # Si tu clave primaria no es UUID, elimina este bloque y usa str(user_id).
        uid = user_id  # type: ignore

    user = crud.get_user(db, uid)  # type: ignore
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
