"""Hierarquia de exceções de domínio/aplicação.

As exceções carregam semântica de negócio (não HTTP). Os *handlers* das camadas
de entrada (API e Web) traduzem essas exceções para respostas apropriadas
(JSON ou HTML), mantendo a lógica de negócio independente do protocolo.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Exceção base da aplicação.

    Attributes:
        message: Mensagem legível para o usuário/desenvolvedor.
        code: Código curto e estável para identificação programática.
        status_code: Código HTTP sugerido para a camada de entrada.
        details: Informações adicionais estruturadas (opcional).
    """

    status_code: int = 400
    code: str = "app_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Serializa a exceção para resposta de API."""
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


class ValidationError(AppError):
    """Dados de entrada inválidos segundo regras de negócio."""

    status_code = 422
    code = "validation_error"


class NotFoundError(AppError):
    """Recurso solicitado não existe (ou não é visível no tenant atual)."""

    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    """Conflito de estado (ex.: violação de unicidade ou regra de negócio)."""

    status_code = 409
    code = "conflict"


class AuthenticationError(AppError):
    """Falha de autenticação (credenciais ausentes ou inválidas)."""

    status_code = 401
    code = "authentication_error"


class PermissionDeniedError(AppError):
    """Usuário autenticado sem permissão para a operação."""

    status_code = 403
    code = "permission_denied"


class TenantResolutionError(AppError):
    """Não foi possível resolver a empresa (tenant) do contexto."""

    status_code = 400
    code = "tenant_resolution_error"


class BusinessRuleError(ConflictError):
    """Violação explícita de uma regra de negócio do domínio."""

    code = "business_rule_violation"
