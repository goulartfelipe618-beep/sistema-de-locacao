"""Enumerações compartilhadas entre módulos."""

from __future__ import annotations

import enum


class TenantStatus(str, enum.Enum):
    """Situação de uma empresa (tenant) na plataforma SaaS."""

    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELED = "canceled"


class FilialStatus(str, enum.Enum):
    """Situação de uma filial/unidade operacional."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class PermissionAction(str, enum.Enum):
    """Ações padronizadas do RBAC (verbo da permissão)."""

    VIEW = "visualizar"
    CREATE = "criar"
    EDIT = "editar"
    DELETE = "excluir"
    APPROVE = "aprovar"
    CANCEL = "cancelar"
    REVERSE = "estornar"
    EXPORT = "exportar"


class PersonType(str, enum.Enum):
    """Tipo de pessoa (usado em clientes, fornecedores, etc.)."""

    NATURAL = "pf"  # Pessoa Física
    LEGAL = "pj"  # Pessoa Jurídica


class AuditAction(str, enum.Enum):
    """Categorias de eventos registrados na trilha de auditoria."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    ACCESS_DENIED = "access_denied"
    EXPORT = "export"
