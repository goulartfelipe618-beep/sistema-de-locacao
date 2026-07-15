"""Núcleo do controle de acesso baseado em papéis (RBAC).

Define:
    * O catálogo de permissões do sistema (fonte única de verdade), no formato
      ``modulo.recurso.acao``.
    * O catálogo de papéis-modelo (templates) semeados por tenant.
    * A lógica pura de verificação de permissões (com suporte a curingas).

A resolução das permissões efetivas de um usuário (a partir de seus papéis) é
responsabilidade do módulo *identity*; aqui ficam apenas as regras puras.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PermissionDef:
    """Definição de uma permissão do sistema."""

    code: str
    module: str
    resource: str
    action: str
    description: str


@dataclass(frozen=True, slots=True)
class RoleTemplate:
    """Definição de um papel-modelo semeado em cada tenant."""

    slug: str
    name: str
    description: str
    is_system: bool = True
    # Lista de códigos de permissão; "*" concede todas.
    permissions: tuple[str, ...] = field(default_factory=tuple)


def _perm(module: str, resource: str, action: str, description: str) -> PermissionDef:
    return PermissionDef(
        code=f"{module}.{resource}.{action}",
        module=module,
        resource=resource,
        action=action,
        description=description,
    )


# ==========================================================================
# CATÁLOGO DE PERMISSÕES DO SISTEMA (Fase 0 - fundação + administração)
# Módulos de negócio adicionarão suas permissões nas próximas fases.
# ==========================================================================
SYSTEM_PERMISSIONS: tuple[PermissionDef, ...] = (
    # ---- Dashboard ----
    _perm("dashboard", "painel", "visualizar", "Visualizar dashboards e KPIs"),
    # ---- Identidade: usuários ----
    _perm("identidade", "usuario", "visualizar", "Visualizar usuários"),
    _perm("identidade", "usuario", "criar", "Criar usuários"),
    _perm("identidade", "usuario", "editar", "Editar usuários"),
    _perm("identidade", "usuario", "excluir", "Excluir usuários"),
    # ---- Identidade: papéis/permissões ----
    _perm("identidade", "papel", "visualizar", "Visualizar papéis e permissões"),
    _perm("identidade", "papel", "criar", "Criar papéis"),
    _perm("identidade", "papel", "editar", "Editar papéis e vincular permissões"),
    _perm("identidade", "papel", "excluir", "Excluir papéis"),
    # ---- Empresa (tenant) ----
    _perm("configuracoes", "empresa", "visualizar", "Visualizar dados da empresa"),
    _perm("configuracoes", "empresa", "editar", "Editar dados da empresa"),
    # ---- Filiais ----
    _perm("configuracoes", "filial", "visualizar", "Visualizar filiais/unidades"),
    _perm("configuracoes", "filial", "criar", "Criar filiais/unidades"),
    _perm("configuracoes", "filial", "editar", "Editar filiais/unidades"),
    _perm("configuracoes", "filial", "excluir", "Excluir filiais/unidades"),
    # ---- Cadastros ----
    _perm("cadastros", "cliente", "visualizar", "Visualizar clientes"),
    _perm("cadastros", "cliente", "criar", "Criar clientes"),
    _perm("cadastros", "cliente", "editar", "Editar clientes"),
    _perm("cadastros", "cliente", "excluir", "Excluir clientes"),
    _perm("cadastros", "cliente", "bloquear", "Bloquear clientes / blacklist"),
    _perm("cadastros", "tabela", "visualizar", "Visualizar tabelas auxiliares"),
    _perm("cadastros", "tabela", "criar", "Criar itens de tabelas auxiliares"),
    _perm("cadastros", "tabela", "editar", "Editar tabelas auxiliares"),
    _perm("cadastros", "tabela", "excluir", "Excluir tabelas auxiliares"),
    _perm("cadastros", "motorista", "visualizar", "Visualizar motoristas"),
    _perm("cadastros", "motorista", "criar", "Criar motoristas"),
    _perm("cadastros", "motorista", "editar", "Editar motoristas"),
    _perm("cadastros", "motorista", "excluir", "Excluir motoristas"),
    _perm("cadastros", "parceiro", "visualizar", "Visualizar parceiros"),
    _perm("cadastros", "parceiro", "criar", "Criar parceiros"),
    _perm("cadastros", "parceiro", "editar", "Editar parceiros"),
    _perm("cadastros", "parceiro", "excluir", "Excluir parceiros"),
    _perm("cadastros", "fornecedor", "visualizar", "Visualizar fornecedores"),
    _perm("cadastros", "fornecedor", "criar", "Criar fornecedores"),
    _perm("cadastros", "fornecedor", "editar", "Editar fornecedores"),
    _perm("cadastros", "fornecedor", "excluir", "Excluir fornecedores"),
    _perm("cadastros", "vendedor", "visualizar", "Visualizar vendedores"),
    _perm("cadastros", "vendedor", "criar", "Criar vendedores"),
    _perm("cadastros", "vendedor", "editar", "Editar vendedores"),
    _perm("cadastros", "vendedor", "excluir", "Excluir vendedores"),
    # ---- Frota ----
    _perm("frota", "veiculo", "visualizar", "Visualizar veículos"),
    _perm("frota", "veiculo", "criar", "Criar veículos"),
    _perm("frota", "veiculo", "editar", "Editar veículos"),
    _perm("frota", "veiculo", "excluir", "Excluir veículos"),
    _perm("frota", "veiculo", "bloquear", "Bloquear veículos"),
    _perm("frota", "veiculo", "baixar", "Baixar veículos (venda/sinistro)"),
    _perm("frota", "categoria", "visualizar", "Visualizar categorias de frota"),
    _perm("frota", "categoria", "criar", "Criar categorias de frota"),
    _perm("frota", "categoria", "editar", "Editar categorias de frota"),
    _perm("frota", "categoria", "excluir", "Excluir categorias de frota"),
    _perm("frota", "marca", "visualizar", "Visualizar marcas"),
    _perm("frota", "marca", "criar", "Criar marcas"),
    _perm("frota", "marca", "editar", "Editar marcas"),
    _perm("frota", "marca", "excluir", "Excluir marcas"),
    _perm("frota", "modelo", "visualizar", "Visualizar modelos"),
    _perm("frota", "modelo", "criar", "Criar modelos"),
    _perm("frota", "modelo", "editar", "Editar modelos"),
    _perm("frota", "modelo", "excluir", "Excluir modelos"),
    _perm("frota", "combustivel", "visualizar", "Visualizar combustíveis"),
    _perm("frota", "combustivel", "criar", "Criar combustíveis"),
    _perm("frota", "combustivel", "editar", "Editar combustíveis"),
    _perm("frota", "combustivel", "excluir", "Excluir combustíveis"),
    _perm("frota", "acessorio", "visualizar", "Visualizar acessórios"),
    _perm("frota", "acessorio", "criar", "Criar acessórios"),
    _perm("frota", "acessorio", "editar", "Editar acessórios"),
    _perm("frota", "acessorio", "excluir", "Excluir acessórios"),
    _perm("frota", "documentacao", "visualizar", "Visualizar documentação de veículos"),
    _perm("frota", "documentacao", "criar", "Criar documentação de veículos"),
    _perm("frota", "documentacao", "editar", "Editar documentação de veículos"),
    _perm("frota", "documentacao", "excluir", "Excluir documentação de veículos"),
    _perm("frota", "telemetria", "visualizar", "Visualizar telemetria"),
    _perm("frota", "telemetria", "criar", "Cadastrar dispositivos de telemetria"),
    _perm("frota", "telemetria", "editar", "Editar telemetria / registrar eventos"),
    _perm("frota", "telemetria", "excluir", "Excluir dispositivos de telemetria"),
    # ---- Auditoria / Logs ----
    _perm("auditoria", "trilha", "visualizar", "Visualizar trilha de auditoria"),
    _perm("logs", "sistema", "visualizar", "Visualizar logs do sistema"),
    # ---- Administração SaaS (super-admin) ----
    _perm("admin", "tenant", "visualizar", "Visualizar empresas (tenants) da plataforma"),
    _perm("admin", "tenant", "criar", "Criar empresas (tenants)"),
    _perm("admin", "tenant", "editar", "Editar empresas (tenants)"),
)

# Índice por código para consultas rápidas.
PERMISSIONS_BY_CODE: dict[str, PermissionDef] = {p.code: p for p in SYSTEM_PERMISSIONS}


# ==========================================================================
# CATÁLOGO DE PAPÉIS-MODELO (semeados por tenant)
# ==========================================================================
ADMIN_EMPRESA = RoleTemplate(
    slug="admin-empresa",
    name="Administrador da Empresa",
    description="Acesso total dentro da própria empresa (tenant).",
    permissions=("*",),
)

GERENTE_FILIAL = RoleTemplate(
    slug="gerente-filial",
    name="Gerente de Filial",
    description="Gestão operacional e relatórios no escopo da(s) filial(is).",
    permissions=(
        "dashboard.painel.visualizar",
        "identidade.usuario.visualizar",
        "configuracoes.empresa.visualizar",
        "configuracoes.filial.visualizar",
        "configuracoes.filial.editar",
        "cadastros.cliente.visualizar",
        "cadastros.cliente.criar",
        "cadastros.cliente.editar",
        "cadastros.cliente.bloquear",
        "cadastros.tabela.visualizar",
        "cadastros.motorista.visualizar",
        "cadastros.motorista.criar",
        "cadastros.motorista.editar",
        "cadastros.parceiro.visualizar",
        "cadastros.parceiro.criar",
        "cadastros.parceiro.editar",
        "cadastros.fornecedor.visualizar",
        "cadastros.fornecedor.criar",
        "cadastros.fornecedor.editar",
        "cadastros.vendedor.visualizar",
        "cadastros.vendedor.criar",
        "cadastros.vendedor.editar",
        "frota.veiculo.visualizar",
        "frota.veiculo.criar",
        "frota.veiculo.editar",
        "frota.veiculo.bloquear",
        "frota.categoria.visualizar",
        "frota.categoria.criar",
        "frota.categoria.editar",
        "frota.marca.visualizar",
        "frota.marca.criar",
        "frota.marca.editar",
        "frota.modelo.visualizar",
        "frota.modelo.criar",
        "frota.modelo.editar",
        "frota.combustivel.visualizar",
        "frota.combustivel.criar",
        "frota.combustivel.editar",
        "frota.acessorio.visualizar",
        "frota.acessorio.criar",
        "frota.acessorio.editar",
        "frota.documentacao.visualizar",
        "frota.documentacao.criar",
        "frota.documentacao.editar",
        "frota.telemetria.visualizar",
        "frota.telemetria.criar",
        "frota.telemetria.editar",
        "auditoria.trilha.visualizar",
    ),
)

OPERADOR = RoleTemplate(
    slug="operador",
    name="Operador de Balcão",
    description="Operações do dia a dia (atendimento, reservas, contratos).",
    permissions=(
        "dashboard.painel.visualizar",
        "configuracoes.empresa.visualizar",
        "configuracoes.filial.visualizar",
        "cadastros.cliente.visualizar",
        "cadastros.cliente.criar",
        "cadastros.cliente.editar",
        "cadastros.tabela.visualizar",
        "cadastros.motorista.visualizar",
        "cadastros.motorista.criar",
        "cadastros.motorista.editar",
        "cadastros.parceiro.visualizar",
        "cadastros.vendedor.visualizar",
        "cadastros.vendedor.criar",
        "frota.veiculo.visualizar",
        "frota.categoria.visualizar",
        "frota.marca.visualizar",
        "frota.modelo.visualizar",
        "frota.combustivel.visualizar",
        "frota.acessorio.visualizar",
        "frota.documentacao.visualizar",
        "frota.telemetria.visualizar",
    ),
)

AUDITOR = RoleTemplate(
    slug="auditor",
    name="Auditor (Somente Leitura)",
    description="Acesso somente leitura, incluindo trilha de auditoria.",
    permissions=(
        "dashboard.painel.visualizar",
        "identidade.usuario.visualizar",
        "identidade.papel.visualizar",
        "configuracoes.empresa.visualizar",
        "configuracoes.filial.visualizar",
        "cadastros.cliente.visualizar",
        "cadastros.tabela.visualizar",
        "cadastros.motorista.visualizar",
        "cadastros.parceiro.visualizar",
        "cadastros.fornecedor.visualizar",
        "cadastros.vendedor.visualizar",
        "frota.veiculo.visualizar",
        "frota.categoria.visualizar",
        "frota.marca.visualizar",
        "frota.modelo.visualizar",
        "frota.combustivel.visualizar",
        "frota.acessorio.visualizar",
        "frota.documentacao.visualizar",
        "frota.telemetria.visualizar",
        "auditoria.trilha.visualizar",
        "logs.sistema.visualizar",
    ),
)

SYSTEM_ROLE_TEMPLATES: tuple[RoleTemplate, ...] = (
    ADMIN_EMPRESA,
    GERENTE_FILIAL,
    OPERADOR,
    AUDITOR,
)


# ==========================================================================
# LÓGICA PURA DE VERIFICAÇÃO
# ==========================================================================
def expand_permissions(codes: set[str]) -> set[str]:
    """Expande o curinga global ``*`` para todas as permissões do sistema."""
    if "*" in codes:
        return {p.code for p in SYSTEM_PERMISSIONS}
    return codes


def has_permission(
    user_permissions: set[str],
    required: str,
    *,
    is_superuser: bool = False,
) -> bool:
    """Verifica se o conjunto de permissões do usuário satisfaz a exigida.

    Regras:
        * Superusuário tem acesso irrestrito.
        * Curinga global ``*`` concede tudo.
        * Curinga de módulo ``modulo.*`` concede todas as ações do módulo.
        * Caso contrário, exige correspondência exata do código.
    """
    if is_superuser or "*" in user_permissions:
        return True
    if required in user_permissions:
        return True
    module_prefix = required.split(".", 1)[0]
    return f"{module_prefix}.*" in user_permissions
