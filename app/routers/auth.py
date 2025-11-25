# app/routers/auth.py
"""
Rutas de autenticación.

- Login JSON y por form.
- "Olvidé mi contraseña" (forgot).
- Reset de contraseña con código.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime

from app.db import get_db
from app import schemas, crud, models
from app.security import verify_password, create_access_token, get_password_hash
from app.services.emailer import send_email

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ==========================
#   Esquemas internos
# ==========================

class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    email: EmailStr
    code: str
    new_password: str


# ==========================
#   LOGIN
# ==========================

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
        "user": { ...UserOut }
      }
    """
    user = crud.get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
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
    Variante para pruebas desde Swagger / formularios.
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


# ==========================
#   OLVIDÉ MI CONTRASEÑA
# ==========================

@router.post("/password/forgot", summary="Enviar código para restablecer contraseña")
def forgot_password(
    payload: ForgotPasswordIn,
    db: Session = Depends(get_db),
):
    """
    Envía un código de verificación al correo para restablecer contraseña.
    Reusa la misma tabla 'verification_codes'.
    """
    user = crud.get_user_by_email(db, payload.email)
    if not user:
        # No revelamos si existe o no, pero tú prefieres mensaje explícito:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    #    # Crea código en BD e invalida los anteriores
    code = crud.create_verification_code(db, user)

    # Construimos el correo usando el mismo servicio send_email
    subject = "Código para restablecer contraseña - Conexión Carga"
    text = (
        f"Hola {user.first_name},\n\n"
        f"Tu código para restablecer tu contraseña es: {code}\n"
        "Este código vence en 5 minutos.\n\n"
        "Si no solicitaste este cambio, ignora este mensaje."
    )
    html = f"""
        <p>Hola {user.first_name},</p>
        <p>Tu código para restablecer la contraseña es:
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

    return {"detail": "Código enviado para restablecer contraseña"}



@router.post("/password/reset", summary="Restablecer contraseña")
def reset_password(
    payload: ResetPasswordIn,
    db: Session = Depends(get_db),
):
    """
    Cambia la contraseña siempre que:
    - El usuario exista
    - El código exista, esté asociado a ese usuario
    - El código no esté usado y no esté expirado
    """
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

    if not verif or verif.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Código inválido o expirado")

    # marcar el código como usado y actualizar contraseña
    verif.used = True
    user.password_hash = get_password_hash(payload.new_password)

    db.add(user)
    db.add(verif)
    db.commit()

    return {"detail": "Contraseña actualizada correctamente"}
