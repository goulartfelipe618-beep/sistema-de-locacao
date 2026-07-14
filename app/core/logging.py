"""Configuração de logging estruturado.

Em produção, os logs são emitidos em JSON (uma linha por evento) com
``correlation_id``/``tenant_id``/``user_id`` embutidos, facilitando a coleta
por agregadores. Em desenvolvimento, um formato legível é usado.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.core.context import get_correlation_id, get_tenant_id, get_user_id

_RESERVED_ATTRS = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename", "funcName",
    "levelname", "levelno", "lineno", "module", "msecs", "message", "msg", "name",
    "pathname", "process", "processName", "relativeCreated", "stack_info",
    "thread", "threadName", "taskName",
}


class ContextFilter(logging.Filter):
    """Injeta dados do contexto de execução em cada registro de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        tenant = get_tenant_id()
        user = get_user_id()
        record.tenant_id = str(tenant) if tenant else None
        record.user_id = str(user) if user else None
        return True


class JsonFormatter(logging.Formatter):
    """Formata registros de log como JSON estruturado."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
            "tenant_id": getattr(record, "tenant_id", None),
            "user_id": getattr(record, "user_id", None),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED_ATTRS and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class HumanFormatter(logging.Formatter):
    """Formato legível para desenvolvimento, com contexto resumido."""

    default_fmt = "%(asctime)s | %(levelname)-7s | %(name)s | cid=%(correlation_id)s | %(message)s"

    def __init__(self) -> None:
        super().__init__(fmt=self.default_fmt, datefmt="%Y-%m-%d %H:%M:%S")


def configure_logging() -> None:
    """Configura o logging global da aplicação (idempotente)."""
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextFilter())
    handler.setFormatter(JsonFormatter() if settings.log_json else HumanFormatter())
    root.addHandler(handler)

    # Reduz ruído de bibliotecas de terceiros.
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "aiobotocore", "botocore", "boto3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("uvicorn.error").setLevel(settings.log_level)


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger nomeado já integrado ao contexto da aplicação."""
    return logging.getLogger(name)
