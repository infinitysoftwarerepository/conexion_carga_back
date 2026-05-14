from __future__ import annotations

import os
import html
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.db import get_db
from app.security import get_current_user
from app.services.emailer import send_email

router = APIRouter(prefix="/user", tags=["Account deletion"])


@router.post(
    "/request-account-deletion",
    response_model=schemas.AccountDeletionOut,
)
def request_account_deletion(
    payload: schemas.AccountDeletionRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    motivo = payload.motivo.strip()
    if len(motivo) < 10 or len(motivo) > 200:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El motivo debe tener entre 10 y 200 caracteres.",
        )

    if str(payload.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes solicitar la eliminación de otra cuenta.",
        )

    if str(payload.email).strip().lower() != str(current_user.email).strip().lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El correo no corresponde al usuario autenticado.",
        )

    user = crud.get_user(db, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    admin_mail = (os.getenv("ADMIN_MAIL") or os.getenv("SMTP_USER") or "").strip()
    if not admin_mail:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ADMIN_MAIL no está configurado.",
        )

    fecha = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    nombre = f"{user.first_name} {user.last_name}".strip() or user.email
    subject = "Solicitud de eliminación de cuenta - Conexión Carga"
    text = (
        "Se recibió una solicitud de eliminación de cuenta.\n\n"
        f"ID usuario: {user.id}\n"
        f"Nombre: {nombre}\n"
        f"Email: {user.email}\n"
        f"Fecha: {fecha}\n\n"
        f"Motivo:\n{motivo}\n"
    )
    html_body = f"""
        <p>Se recibió una solicitud de eliminación de cuenta.</p>
        <ul>
            <li><strong>ID usuario:</strong> {html.escape(str(user.id))}</li>
            <li><strong>Nombre:</strong> {html.escape(nombre)}</li>
            <li><strong>Email:</strong> {html.escape(str(user.email))}</li>
            <li><strong>Fecha:</strong> {fecha}</li>
        </ul>
        <p><strong>Motivo:</strong></p>
        <p>{html.escape(motivo)}</p>
    """

    try:
        send_email(admin_mail, subject, text, html_body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No fue posible enviar la solicitud al administrador: {exc}",
        ) from exc

    user.active = False
    db.add(user)
    db.commit()

    return schemas.AccountDeletionOut(success=True)
