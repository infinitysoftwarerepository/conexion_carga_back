"""
Servicio de envío de correos vía SMTP (Gmail).
Usa App Password de 16 caracteres (variable de entorno SMTP_PASS).
"""

import os
import ssl
import smtplib
from email.message import EmailMessage

# Carga desde .env / entorno
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")       # Servidor SMTP (Gmail)
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))             # Puerto STARTTLS típico
SMTP_USER = os.getenv("SMTP_USER")                         # Cuenta remitente
SMTP_PASS = os.getenv("SMTP_PASS")                         # App Password (16 chars, sin espacios)
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)            # "Nombre <correo@...>"

def send_email(to_email: str, subject: str, text_body: str, html_body: str | None = None) -> None:
    """
    Envía un correo a 'to_email' con asunto 'subject'.
    Incluye versión de texto plano y opcionalmente HTML.
    Lanza excepción si faltan credenciales o si el envío falla.
    """
    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("SMTP_USER/SMTP_PASS no configurados. Revisa tu .env")

    # Construcción del mensaje con cabeceras estándar
    msg = EmailMessage()
    msg["From"] = EMAIL_FROM or SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(text_body)                  # Parte de texto (fallback)
    if html_body:
        msg.add_alternative(html_body, subtype="html")  # Parte HTML (opcional)

    # Cliente SMTP con STARTTLS
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls(context=ssl.create_default_context()) # Cifra la conexión
        s.login(SMTP_USER, SMTP_PASS)                    # Autenticación App Password
        s.send_message(msg)                              # Enviar
