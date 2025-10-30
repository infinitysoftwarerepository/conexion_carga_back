# app/routers/auth.py
"""
Rutas de autenticación.

CAMBIOS CLAVE:
- response_model=TokenOut ahora coincide con el JSON que devolvemos
  (access_token + token_type + user opcional).
- Devolvemos también 'user' para que el cliente tenga el perfil inmediatamente
  (evita un /me justo después de loguear).
- Usamos response_model_exclude_none=True para no forzar 'user' si no lo quieres incluir.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session

from app.db import get_db
from app import schemas, crud
from app.security import verify_password, create_access_token  # ya existente

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post(
    "/login",
    response_model=schemas.TokenOut,
    response_model_exclude_none=True,
    summary="Login (JSON)",
)
def login_json(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    """
    Inicia sesión con JSON:
      { "email": "...", "password": "..." }

    Respuesta (coincide con schemas.TokenOut):
      {
        "access_token": "<JWT>",
        "token_type": "bearer",
        "user": { ...UserOut }   # opcional pero recomendado
      }
    """
    user = crud.get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )

    token = create_access_token({"sub": str(user.id)})

    # Construimos UserOut para no filtrar campos sensibles y mantener
    # el contrato estable entre back y front.
    user_out = schemas.UserOut.model_validate(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_out,
    }


@router.post(
    "/login-form",
    response_model=schemas.TokenOut,
    response_model_exclude_none=True,
    summary="Login (form-url-encoded)",
)
def login_form(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Variante para facilitar pruebas desde Swagger o formularios
    application/x-www-form-urlencoded.
    """
    user = crud.get_user_by_email(db, email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )

    token = create_access_token({"sub": str(user.id)})
    user_out = schemas.UserOut.model_validate(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_out,
    }
