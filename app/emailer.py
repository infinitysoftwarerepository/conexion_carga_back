"""
Servicio de envío de correos vía SMTP (por ejemplo Gmail).
Usa App Password de 16 caracteres (variable de entorno SMTP_PASS).
"""

import os
import ssl
import smtplib
from email.message import EmailMessage

# Configuración desde .env
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")   # Servidor SMTP
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))         # Puerto STARTTLS
SMTP_USER = os.getenv("SMTP_USER")                     # Cuenta de correo remitente
SMTP_PASS = os.getenv("SMTP_PASS")                     # App Password
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)        # Nombre visible del remitente

def send_email(to_email: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    """
    Envía un correo con versión texto y opcionalmente HTML.
    Lanza excepción si falla.
    """

    # 1️⃣ Validar credenciales
    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("SMTP_USER/SMTP_PASS no configurados en .env")

    # 2️⃣ Crear el mensaje de correo
    msg = EmailMessage()
    msg["From"] = EMAIL_FROM or SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    # 3️⃣ Conectar al servidor y enviar
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls(context=ssl.create_default_context())  # conexión segura
        s.login(SMTP_USER, SMTP_PASS)                     # autenticación
        s.send_message(msg)                               # enviar mensaje
