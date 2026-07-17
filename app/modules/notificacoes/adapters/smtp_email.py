"""Adaptador SMTP para envio real de e-mail."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import settings


class SmtpEmail:
    """Envia e-mail via SMTP configurado em variáveis de ambiente."""

    def send(self, *, to: str, subject: str, body: str) -> None:
        if not settings.smtp_host:
            raise RuntimeError("SMTP_HOST não configurado.")
        from_addr = settings.smtp_from or settings.smtp_user or "noreply@localhost"
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to
        msg.set_content(body)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
