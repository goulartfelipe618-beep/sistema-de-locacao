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


class ClienteStatus(str, enum.Enum):
    """Situação cadastral do cliente."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class CadastroStatus(str, enum.Enum):
    """Situação genérica ativo/inativo para cadastros mestre."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class MotoristaVinculo(str, enum.Enum):
    """Tipo de vínculo do motorista."""

    CLIENTE = "cliente"
    FUNCIONARIO = "funcionario"
    TERCEIRO = "terceiro"


class MotoristaCnhStatus(str, enum.Enum):
    """Situação da CNH do motorista."""

    REGULAR = "regular"
    VENCIDA = "vencida"
    SUSPENSA = "suspensa"
    CASSADA = "cassada"


class ParceiroTipo(str, enum.Enum):
    """Tipo de parceria comercial."""

    INDICACAO = "indicacao"
    WHITE_LABEL = "white_label"
    FRANQUIA = "franquia"
    MARKETPLACE = "marketplace"


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
