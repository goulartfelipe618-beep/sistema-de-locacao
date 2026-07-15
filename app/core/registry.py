"""Registro central de modelos ORM.

Importar este módulo garante que **todas** as tabelas sejam registradas na
``Base.metadata`` — essencial para o *autogenerate* do Alembic e para a criação
consistente do schema. Novos módulos devem adicionar seus imports aqui.
"""

from __future__ import annotations

from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.cadastros import models as cadastros_models  # noqa: F401
from app.modules.comercial import models as comercial_models  # noqa: F401
from app.modules.financeiro import models as financeiro_models  # noqa: F401
from app.modules.fiscal import models as fiscal_models  # noqa: F401
from app.modules.frota import models as frota_models  # noqa: F401
from app.modules.identity import models as identity_models  # noqa: F401
from app.modules.locacoes import models as locacoes_models  # noqa: F401
from app.modules.manutencao import models as manutencao_models  # noqa: F401
from app.modules.reservas import models as reservas_models  # noqa: F401
from app.modules.tarifario import models as tarifario_models  # noqa: F401

# Ordem de import respeita dependências de chave estrangeira.
from app.modules.tenants import models as tenants_models  # noqa: F401
from app.shared.base_model import Base

__all__ = [
    "Base",
    "tenants_models",
    "identity_models",
    "audit_models",
    "cadastros_models",
    "comercial_models",
    "financeiro_models",
    "fiscal_models",
    "frota_models",
    "locacoes_models",
    "manutencao_models",
    "reservas_models",
    "tarifario_models",
]
