import os
import smtplib
from email.message import EmailMessage

def send_email(email: str, subject: str, body: str):
    """
    Envía un correo electrónico utilizando SMTP de Gmail.
    """
    gmail_user = "developerdaniel733@gmail.com" #os.getenv("GMAIL_USER")  # Tu email de Gmail
    gmail_pass = "djrmprxaufdkatim" #os.getenv("GMAIL_PASS")  # Tu contraseña o App Password

    if not gmail_user or not gmail_pass:
        print("Faltan las variables de entorno GMAIL_USER o GMAIL_PASS")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = email
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.send_message(msg)
        return f"Correo enviado a {email} correctamente."
    except Exception as e:
        return f"Error enviando correo: {e}"

def send_validation_email(email, token):
    """
    Envía el email de validación al usuario usando SMTP de Gmail.
    """
    FRONTEND_URL = os.getenv("FRONTEND_URL", "https://digitalcrm.net")
    validation_link = f"{FRONTEND_URL}/validate-email?token={token}"
    
    subject = "Valida tu cuenta"
    body = f"""Hola,
        Para validar tu cuenta, haz clic en el siguiente enlace:
        {validation_link}

        Si no solicitaste este registro, puedes ignorar este mensaje.
    """

    return send_email(email, subject, body)
