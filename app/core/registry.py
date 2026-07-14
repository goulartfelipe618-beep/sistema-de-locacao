"""Registro central de modelos ORM.

Importar este módulo garante que **todas** as tabelas sejam registradas na
``Base.metadata`` — essencial para o *autogenerate* do Alembic e para a criação
consistente do schema. Novos módulos devem adicionar seus imports aqui.
"""

from __future__ import annotations

from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.identity import models as identity_models  # noqa: F401

# Ordem de import respeita dependências de chave estrangeira.
from app.modules.tenants import models as tenants_models  # noqa: F401
from app.shared.base_model import Base

__all__ = ["Base", "tenants_models", "identity_models", "audit_models"]
