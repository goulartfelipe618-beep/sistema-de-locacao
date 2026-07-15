"""Árvore de navegação do painel administrativo.

Define a estrutura completa do menu lateral do ERP (todos os módulos previstos
na arquitetura). Itens ainda não implementados nesta fase aparecem desabilitados,
preservando a visão de amplitude do sistema. Itens implementados são exibidos
conforme as permissões (RBAC) do usuário.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.core.rbac import has_permission

if TYPE_CHECKING:
    from app.modules.identity.service import AuthenticatedUser


@dataclass(frozen=True, slots=True)
class MenuItem:
    """Item de menu (folha)."""

    label: str
    url: str | None = None
    permission: str | None = None
    implemented: bool = False


@dataclass(frozen=True, slots=True)
class MenuSection:
    """Seção do menu (com ícone e itens)."""

    label: str
    icon: str
    items: tuple[MenuItem, ...] = field(default_factory=tuple)
    url: str | None = None  # seção com link direto (ex.: Dashboard)
    permission: str | None = None
    implemented: bool = False


# ==========================================================================
# ESTRUTURA COMPLETA DO MENU (arquitetura aprovada)
# ==========================================================================
NAVIGATION: tuple[MenuSection, ...] = (
    MenuSection(
        label="Dashboard",
        icon="dashboard",
        url="/",
        permission="dashboard.painel.visualizar",
        implemented=True,
    ),
    MenuSection(
        label="Cadastros",
        icon="users",
        items=(
            MenuItem(
                "Clientes",
                url="/cadastros/clientes",
                permission="cadastros.cliente.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Motoristas",
                url="/cadastros/motoristas",
                permission="cadastros.motorista.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Parceiros",
                url="/cadastros/parceiros",
                permission="cadastros.parceiro.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Fornecedores",
                url="/cadastros/fornecedores",
                permission="cadastros.fornecedor.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Vendedores",
                url="/cadastros/vendedores",
                permission="cadastros.vendedor.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Tabelas Auxiliares",
                url="/cadastros/tabelas",
                permission="cadastros.tabela.visualizar",
                implemented=True,
            ),
        ),
    ),
    MenuSection(
        label="Frota",
        icon="car",
        items=(
            MenuItem(
                "Veículos",
                url="/frota/veiculos",
                permission="frota.veiculo.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Categorias",
                url="/frota/categorias",
                permission="frota.categoria.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Marcas",
                url="/frota/marcas",
                permission="frota.marca.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Modelos",
                url="/frota/modelos",
                permission="frota.modelo.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Combustíveis",
                url="/frota/combustiveis",
                permission="frota.combustivel.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Acessórios",
                url="/frota/acessorios",
                permission="frota.acessorio.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Documentação",
                url="/frota/documentacao",
                permission="frota.documentacao.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Telemetria",
                url="/frota/telemetria",
                permission="frota.telemetria.visualizar",
                implemented=True,
            ),
        ),
    ),
    MenuSection(
        label="Manutenção",
        icon="wrench",
        items=(
            MenuItem(
                "Ordens de Serviço",
                url="/manutencao/os",
                permission="manutencao.os.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Preventiva",
                url="/manutencao/preventiva",
                permission="manutencao.preventiva.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Corretiva",
                url="/manutencao/corretiva",
                permission="manutencao.corretiva.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Peças / Estoque",
                url="/manutencao/pecas",
                permission="manutencao.peca.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Pneus",
                url="/manutencao/pneus",
                permission="manutencao.pneu.visualizar",
                implemented=True,
            ),
        ),
    ),
    MenuSection(
        label="Reservas",
        icon="calendar",
        items=(
            MenuItem("Nova Reserva", url="/reservas/nova"),
            MenuItem("Reservas", url="/reservas"),
            MenuItem("Calendário", url="/reservas/calendario"),
            MenuItem("Disponibilidade", url="/reservas/disponibilidade"),
            MenuItem("Cotações", url="/reservas/cotacoes"),
        ),
    ),
    MenuSection(
        label="Locações",
        icon="contract",
        items=(
            MenuItem("Contratos", url="/locacoes/contratos"),
            MenuItem("Check-out", url="/locacoes/checkout"),
            MenuItem("Check-in", url="/locacoes/checkin"),
            MenuItem("Renovações", url="/locacoes/renovacoes"),
            MenuItem("Encerramentos", url="/locacoes/encerramentos"),
            MenuItem("Multas e Infrações", url="/locacoes/multas"),
            MenuItem("Avarias", url="/locacoes/avarias"),
        ),
    ),
    MenuSection(
        label="Comercial / CRM",
        icon="target",
        items=(
            MenuItem("Funil de Vendas", url="/crm/funil"),
            MenuItem("Propostas", url="/crm/propostas"),
            MenuItem("Campanhas", url="/crm/campanhas"),
            MenuItem("Cupons", url="/crm/cupons"),
            MenuItem("Fidelidade", url="/crm/fidelidade"),
        ),
    ),
    MenuSection(
        label="Tarifário",
        icon="tag",
        items=(
            MenuItem("Tabelas de Tarifas", url="/tarifario/tabelas"),
            MenuItem("Temporadas", url="/tarifario/temporadas"),
            MenuItem("Taxas e Encargos", url="/tarifario/taxas"),
            MenuItem("Proteções", url="/tarifario/protecoes"),
            MenuItem("Políticas de Cancelamento", url="/tarifario/cancelamento"),
        ),
    ),
    MenuSection(
        label="Financeiro",
        icon="cash",
        items=(
            MenuItem("Caixa", url="/financeiro/caixa"),
            MenuItem("Contas a Receber", url="/financeiro/receber"),
            MenuItem("Contas a Pagar", url="/financeiro/pagar"),
            MenuItem("PIX", url="/financeiro/pix"),
            MenuItem("Cartões", url="/financeiro/cartoes"),
            MenuItem("Bancos", url="/financeiro/bancos"),
            MenuItem("Conciliação", url="/financeiro/conciliacao"),
            MenuItem("Faturamento", url="/financeiro/faturamento"),
        ),
    ),
    MenuSection(
        label="Fiscal",
        icon="file",
        items=(
            MenuItem("NFS-e", url="/fiscal/nfse"),
            MenuItem("NF-e", url="/fiscal/nfe"),
            MenuItem("XML", url="/fiscal/xml"),
            MenuItem("Cancelamentos", url="/fiscal/cancelamentos"),
            MenuItem("Impostos", url="/fiscal/impostos"),
        ),
    ),
    MenuSection(
        label="Relatórios",
        icon="chart",
        items=(
            MenuItem("Frota", url="/relatorios/frota"),
            MenuItem("Locação", url="/relatorios/locacao"),
            MenuItem("Financeiro", url="/relatorios/financeiro"),
            MenuItem("Fiscal", url="/relatorios/fiscal"),
            MenuItem("Gerencial", url="/relatorios/gerencial"),
        ),
    ),
    MenuSection(
        label="Integrações",
        icon="plug",
        items=(
            MenuItem("Pagamentos", url="/integracoes/pagamentos"),
            MenuItem("Trânsito (DETRAN)", url="/integracoes/transito"),
            MenuItem("Crédito", url="/integracoes/credito"),
            MenuItem("Telemetria", url="/integracoes/telemetria"),
            MenuItem("API Pública", url="/integracoes/api"),
        ),
    ),
    MenuSection(
        label="Automações",
        icon="bolt",
        items=(
            MenuItem("Regras", url="/automacoes/regras"),
            MenuItem("Workflows", url="/automacoes/workflows"),
            MenuItem("Agendamentos", url="/automacoes/agendamentos"),
            MenuItem("Histórico", url="/automacoes/historico"),
        ),
    ),
    MenuSection(
        label="Configurações",
        icon="settings",
        items=(
            MenuItem(
                "Dados da Empresa",
                url="/configuracoes/empresa",
                permission="configuracoes.empresa.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Filiais / Unidades",
                url="/configuracoes/filiais",
                permission="configuracoes.filial.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Usuários",
                url="/configuracoes/usuarios",
                permission="identidade.usuario.visualizar",
                implemented=True,
            ),
            MenuItem(
                "Papéis e Permissões",
                url="/configuracoes/papeis",
                permission="identidade.papel.visualizar",
                implemented=True,
            ),
            MenuItem("Parâmetros", url="/configuracoes/parametros"),
        ),
    ),
    MenuSection(
        label="Auditoria",
        icon="shield",
        items=(
            MenuItem(
                "Trilha de Auditoria",
                url="/auditoria/trilha",
                permission="auditoria.trilha.visualizar",
                implemented=True,
            ),
        ),
    ),
)


def _item_state(item: MenuItem, user: AuthenticatedUser) -> dict | None:
    """Calcula visibilidade/habilitação de um item para o usuário."""
    allowed = item.permission is None or has_permission(
        user.permissions, item.permission, is_superuser=user.is_superuser
    )
    if item.implemented:
        if not allowed:
            return None
        return {"label": item.label, "url": item.url, "enabled": True}
    # Item de módulo futuro: exibido, porém desabilitado ("em breve").
    return {"label": item.label, "url": None, "enabled": False}


def build_menu(user: AuthenticatedUser | None) -> list[dict]:
    """Constrói a árvore de menu já filtrada/anotada para o usuário atual."""
    if user is None:
        return []

    sections: list[dict] = []
    for section in NAVIGATION:
        # Seção com link direto (sem submenu), ex.: Dashboard.
        if not section.items:
            allowed = section.permission is None or has_permission(
                user.permissions, section.permission, is_superuser=user.is_superuser
            )
            if section.implemented and not allowed:
                continue
            sections.append(
                {
                    "label": section.label,
                    "icon": section.icon,
                    "url": section.url if section.implemented else None,
                    "enabled": section.implemented and allowed,
                    # Evitar chave "items": em Jinja dict.items é o método dict.items().
                    "children": [],
                }
            )
            continue

        children = [state for item in section.items if (state := _item_state(item, user))]
        if not children:
            continue
        sections.append(
            {
                "label": section.label,
                "icon": section.icon,
                "url": None,
                "enabled": True,
                "children": children,
            }
        )
    return sections
