"""Registry de provedores de notificação."""

from __future__ import annotations

from app.core.config import settings
from app.modules.notificacoes.adapters.email_port import EmailPort
from app.modules.notificacoes.adapters.simulador_email import SimuladorEmail
from app.modules.notificacoes.adapters.simulador_sms import SimuladorSms
from app.modules.notificacoes.adapters.sms_port import SmsPort
from app.modules.notificacoes.adapters.smtp_email import SmtpEmail


def get_email_provider() -> EmailPort:
    if settings.notification_email_provider == "smtp":
        return SmtpEmail()
    return SimuladorEmail()


def get_sms_provider() -> SmsPort:
    return SimuladorSms()
